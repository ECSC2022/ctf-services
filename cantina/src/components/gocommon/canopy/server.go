package canopy

import (
	"cantina/common/can"
	"cantina/common/canopy/fields"
	"cantina/common/canopy/messages"
	"cantina/common/cipher"
	"cantina/common/components"
	"fmt"
	"log"
	"time"
)

type Server struct {
	cipher         *cipher.Cipher
	sendQueue      chan<- *can.Message
	stopLoop       chan interface{}
	sessionManager *ServerSessionManager
	messageIds     MessageIds
	log            *log.Logger
	sessionInit    SessionInitialization
	replyBuilder   ReplyBuilder
}

func NewServer(
	cipher *cipher.Cipher,
	sendQueue chan<- *can.Message,
	messageIds MessageIds,
	log *log.Logger,
) (server *Server, err error) {
	server = &Server{
		cipher:         cipher,
		sendQueue:      sendQueue,
		stopLoop:       make(chan interface{}, 1),
		sessionManager: NewServerSessionManager(),
		messageIds:     messageIds,
		log:            log,
	}

	// Set default implementations
	server.SetSessionInitializer(server)
	server.SetReplyBuilder(server)
	return
}

func (s *Server) RecvHandlers() (
	handlers map[uint32]components.RecvHandler,
) {
	handlers = make(map[uint32]components.RecvHandler)
	handlers[s.messageIds.Start] = func(
		canMsg *can.Message,
	) error {
		return s.handleSessionStart(canMsg)
	}
	handlers[s.messageIds.Data] = func(
		canMsg *can.Message,
	) error {
		return s.handleSessionData(canMsg)
	}
	return
}

func (s *Server) sendReplyStart(
	sessionId fields.Session,
	state *SessionState,
	length fields.MessageLength,
	extraData fields.ExtraData,
) (err error) {
	msg := messages.SessionStart{}
	err = messages.SessionMessageFromPlaintext(
		&msg,
		state.cipher,
		nil,
		&sessionId,
		&length,
		&extraData,
	)
	if err != nil {
		return
	}

	canMsg, err := messages.SessionMessageToCan(
		&msg,
		s.messageIds.ReplyStart,
	)
	if err != nil {
		return
	}

	s.sendQueue <- canMsg
	return
}

func (s *Server) sendReplyData(
	sessionId fields.Session,
	state *SessionState,
	data []byte,
) (err error) {
	msg := messages.SessionData{}
	chunk_size := can.CANFD_MAX_PAYLOAD -
		messages.SessionMessageMinLength(&msg)

	for offset := 0; offset < len(data); offset += chunk_size {
		end := offset + chunk_size
		if end > len(data) {
			end = len(data)
		}

		chunk := data[offset:end]
		seq := fields.SequenceNumber{
			Value: uint8(offset / chunk_size),
		}
		err = messages.SessionMessageFromPlaintext(
			&msg,
			state.cipher,
			chunk,
			&sessionId,
			&seq,
		)
		if err != nil {
			return
		}

		var canMsg *can.Message
		canMsg, err = messages.SessionMessageToCan(
			&msg,
			s.messageIds.ReplyData,
		)
		if err != nil {
			return
		}

		s.sendQueue <- canMsg
	}

	return
}

func (s *Server) processSession(
	sessionId fields.Session,
	state *ServerSession,
) {
	var localState *SessionState

	// The function needs to be called as goroutine
	defer func() { recover() }()

	// Wait until we get a valid start message
StartLoop:
	for {
		select {
		case canMsg := <-state.SessionChannel:
			// Ignore all messages except start
			if canMsg.ArbitrationId != s.messageIds.Start {
				continue
			}

			// STEP 1: Received session start
			// --------------------------------------------
			// We received a session start packet, before
			// we verify the integrity, check if we already
			// have an open session with the same ID.
			//
			// If we don't have an open session, verify the
			// integrity, then create the session structure
			// in our session table.
			msg := messages.SessionStart{}
			err := messages.SessionMessageFromCan(
				&msg,
				canMsg,
			)
			if err != nil {
				err = fmt.Errorf(
					"Message not in expected "+
						"format for given message "+
						"ID: %w",
					err,
				)
				continue
			}

			// Create new local session state
			localState = NewSession()
			localState.remainingBytes = int(
				msg.Length.Value,
			)
			localState.StartData = msg.ExtraData.Value
			s.sessionInit.InitializeSession(
				msg.SessionId,
				localState,
			)

			// Try to decrypt the message, checking the
			// authentication tag as well.
			_, err = messages.SessionMessageToPlaintext(
				&msg,
				localState.cipher,
			)
			if err != nil {
				// If we can't decrypt the message,
				// it was most likely forged
				continue
			}

			// We have a valid session start message
			break StartLoop
		case <-time.After(SESSION_TIMEOUT):
			// If we didn't get a session start message,
			// we can just time out
			return
		}
	}

	// We can only break out of the above loop if we have a valid
	// local session state (otherwise we return outside of the
	// function.

DataLoop:
	for {
		select {
		case canMsg := <-state.SessionChannel:
			// Ignore all messages except data
			if canMsg.ArbitrationId != s.messageIds.Data {
				continue
			}

			// STEP 2: Receive the data frames from a peer
			// --------------------------------------------
			// Now we're receiving the data frames from the
			// peer, hopefully in order. We're checking the
			// order by only accepting frames that
			// correspond the to correct sequence ID
			msg := messages.SessionData{}
			err := messages.SessionMessageFromCan(
				&msg,
				canMsg,
			)
			if err != nil {
				// Message was not in expected format
				// for given message ID!
				err = fmt.Errorf(
					"Message not in expected "+
						"format for given message "+
						"ID: %w",
					err,
				)
				continue
			}

			// Make sure the sequence numbers match up
			if localState.seq != msg.Seq {
				err = fmt.Errorf(
					"Received invalid sequence "+
						"ID, got %v, expected %v",
					msg.Seq,
					localState.seq,
				)
				continue
			}

			// Decrypt the session data
			pt, err := messages.SessionMessageToPlaintext(
				&msg,
				localState.cipher,
			)
			if err != nil {
				// If we can't decrypt the message, it
				// was most likely forged
				continue
			}

			// Check if we still expect enough data
			dataLength := len(pt)
			if dataLength > localState.remainingBytes {
				// This shouldn't be happening given
				// the other precautions (message auth
				// checks), but just checking to be
				// save
				err = fmt.Errorf(
					"Payload bigger than "+
						"expected, got %v, "+
						"expected %v",
					dataLength,
					localState.remainingBytes,
				)
				continue
			}

			// Add data to buffer and check if we're done
			// reading, otherwise refresh the session
			localState.addData(pt)
			payload := localState.receiveNonBlocking()
			if payload == nil {
				state.refresh()
				continue
			}

			// Alright, data is complete now, break loop
			break DataLoop
		case <-time.After(SESSION_TIMEOUT):
			// If we time out here, we can just leave
			// and hopefully the session will be reaped
			return
		}
	}

	// Make sure payload was sent in order (in theory, our sequence
	// number check should have already taken care of that)
	payload := localState.buffer
	cd := new(fields.CipherData)
	if len(payload) < cd.FieldSize() {
		// We need at least the crypto tag to check for
		// authenticity
		s.log.Println("Invalid canopy payload (too small)")
		return
	}
	data := payload[:len(payload)-cd.FieldSize()]
	_, err := cd.FromBytes(payload[len(payload)-cd.FieldSize():])
	if err != nil {
		s.log.Println("Invalid canopy payload (too small)")
		return
	}
	_, err = cd.ToPlainText(localState.cipher, data)
	if err != nil {
		s.log.Printf(
			"Invalid tag for assembled %v",
			sessionId,
		)
		return
	}

	// Data was received fine, now build reply and send it back
	replyData := s.replyBuilder.BuildReply(sessionId, data, localState)
	err = s.sendReplyStart(
		sessionId,
		localState,
		fields.MessageLength{Value: uint16(len(replyData))},
		fields.ExtraData{Value: localState.StartData},
	)
	if err != nil {
		s.log.Printf(
			"Couldn't send canopy reply start: %v",
			err,
		)
		return
	}
	err = s.sendReplyData(sessionId, localState, replyData)
	if err != nil {
		s.log.Printf(
			"Couldn't send canopy reply data: %v",
			err,
		)
		return
	}
}

func (s *Server) handleSessionStart(canMsg *can.Message) (err error) {
	// STEP 1: Received session start
	// ------------------------------------------------------------
	// We received a session start packet, before we
	// verify the integrity, check if we already have
	// an open session with the same ID.
	//
	// If we don't have an open session, verify the
	// integrity, then create the session structure
	// in our session table.
	msg := messages.SessionStart{}
	err = messages.SessionMessageFromCan(&msg, canMsg)
	if err != nil {
		// Message was not in expected format for given
		// message ID!
		err = fmt.Errorf(
			"Message not in expected format for given"+
				"message ID: %w",
			err,
		)
		return
	}

	// Get a session state for the specified session
	state, isNew := s.sessionManager.getSession(msg.SessionId)

	// Handle session in goroutine (if the session is new)
	if isNew {
		go s.processSession(msg.SessionId, state)
	}

	// Send the message in for processing
	state.SendMessage(canMsg)
	return
}

func (s *Server) handleSessionData(canMsg *can.Message) (err error) {
	// STEP 2: Receive the data frames from a peer
	// ------------------------------------------------------------
	// Now we're receiving the data frames from the
	// peer, hopefully in order. We're checking the
	// order by only accepting frames that correspond
	// the to correct sequence ID
	msg := messages.SessionData{}
	err = messages.SessionMessageFromCan(&msg, canMsg)
	if err != nil {
		// Message was not in expected format for given
		// message ID!
		err = fmt.Errorf(
			"Message not in expected format for given"+
				"message ID: %w",
			err,
		)
		return
	}

	// Get a session state for the specified session
	state, _ := s.sessionManager.getSession(msg.SessionId)

	// Send the message in for processing
	state.SendMessage(canMsg)
	return
}

type SessionInitialization interface {
	InitializeSession(sId fields.Session, state *SessionState)
}

func (s *Server) SetSessionInitializer(init SessionInitialization) {
	s.sessionInit = init
}

func (s *Server) InitializeSession(
	sessionId fields.Session,
	state *SessionState,
) {
	state.SetSessionCipher(s.cipher)
}

type ReplyBuilder interface {
	BuildReply(sId fields.Session, message []byte, state *SessionState) []byte
}

func (s *Server) SetReplyBuilder(replyBuilder ReplyBuilder) {
	s.replyBuilder = replyBuilder
}

func (s *Server) BuildReply(
	sId fields.Session,
	message []byte,
	state *SessionState,
) []byte {
	return []byte{}
}

func (s *Server) UpdateLoop() {
	defer close(s.stopLoop)

	for {
		select {
		case _ = <-s.stopLoop:
			return
		case <-time.After(1 * time.Second):
			s.sessionManager.removeStaleSessions()
		}
	}
}

func (s *Server) Shutdown() {
	go func() { s.stopLoop <- nil }()
}
