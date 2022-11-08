package canopy

import (
	"cantina/common/can"
	"cantina/common/canopy/fields"
	"cantina/common/canopy/messages"
	"cantina/common/cipher"
	"cantina/common/components"
	"fmt"
	"log"
)

type Client struct {
	cipher         *cipher.Cipher
	sendQueue      chan<- *can.Message
	sessionManager *sessionManager
	messageIds     MessageIds
	log *log.Logger
}

func NewClient(
	cipher *cipher.Cipher,
	sendQueue chan<- *can.Message,
	messageIds MessageIds,
	log *log.Logger,
) (client *Client, err error) {
	client = &Client{
		cipher:         cipher,
		sendQueue:      sendQueue,
		sessionManager: NewSessionManager(),
		messageIds:     messageIds,
		log: log,
	}
	return
}

func (c *Client) RecvHandlers() (
	handlers map[uint32]components.RecvHandler,
) {
	handlers = make(map[uint32]components.RecvHandler)
	handlers[c.messageIds.ReplyStart] = func(
		canMsg *can.Message,
	) error {
		return c.handleReplyStart(canMsg)
	}
	handlers[c.messageIds.ReplyData] = func(
		canMsg *can.Message,
	) error {
		return c.handleReplyData(canMsg)
	}
	return
}

func (c *Client) Send(data []byte) ([]byte, error) {
	return c.SendWithStartData(data, []byte{})
}

func (c *Client) SendWithStartData(
	data []byte,
	startData []byte,
) (reply []byte, err error) {
	if !c.cipher.Ok() {
		err = fmt.Errorf("Symmetric key not yet available")
		return
	}

	// STEP 0: Wrap the data
	// ------------------------------------------------------------
	// We currently don't have any protection against out of
	// order messages. I don't know if it's *possible* in our
	// case to have out of order messages, but if it is not,
	// we can simply skip this step later on.
	//
	// We're just using an authenticated tag here to later on
	// check, whether the overall data has been transmitted
	// correctly (since we have an auth tag on every message,
	// the only thing that could happen should really only be
	// out-of-order transmission...)
	ciphertext, err := fields.CipherDataFromPlaintext(
		c.cipher,
		[]byte{},
		data,
	)
	if err != nil {
		err = fmt.Errorf("Could not wrap data: %w", err)
		return
	}
	data = ciphertext.ToBytes(data)

	// STEP 1: Session start
	// ------------------------------------------------------------
	// We generate a random session ID and we need the
	// number of bytes of data we want to send. If a session with
	// the same ID already exists, generate a new ID and try agin
	//
	// We don't encrypt anything here, keep all "flow" info
	// in plaintext and only store the order data later on
	// in the encrypted part. But we're still making use of
	// the AEAD scheme, using AD only.
	//
	// Maximum amount of data we can transmit in a session is
	// about 7900, if we have a sequence number of one byte (with
	// the encryption, we can transmit 34 bytes of data, minus
	// what we need for the session_id and sequence number,
	// assuming a 4 byte session ID and 2 byte sequence number)
	sessionId, session := c.sessionManager.freshSession()
	defer c.sessionManager.releaseSession(sessionId)

	// Still STEP 1: Send the session start message
	// ------------------------------------------------------------
	err = c.sendStart(
		sessionId,
		fields.MessageLength{Value: uint16(len(data))},
		fields.ExtraData{Value: session.StartData},
	)
	if err != nil {
		return
	}

	// STEP 2: Send the data across
	// ------------------------------------------------------------
	// For step 2 we're gonna split the data into chunks of
	// our specified size, tag it with session and sequence
	// id and send it across the bus.
	err = c.sendData(sessionId, data)
	if err != nil {
		return
	}

	// STEP 3: Wait for response
	// ------------------------------------------------------------
	reply, err = session.receiveReply()
	return
}

func (c *Client) sendStart(
	sessionId fields.Session,
	length fields.MessageLength,
	extraData fields.ExtraData,
) (err error) {
	msg := messages.SessionStart{}
	err = messages.SessionMessageFromPlaintext(
		&msg,
		c.cipher,
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
		c.messageIds.Start,
	)
	if err != nil {
		return
	}

	c.sendQueue <- canMsg
	return
}

func (c *Client) sendData(
	sessionId fields.Session,
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
			c.cipher,
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
			c.messageIds.Data,
		)
		if err != nil {
			return
		}

		c.sendQueue <- canMsg
	}

	return
}

func (c *Client) handleReplyStart(canMsg *can.Message) (err error) {
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

	session, ok := c.sessionManager.getSession(msg.SessionId)
	if !ok {
		// Not our session (or possible error)
		// Should we re-transmit in that case?
		err = fmt.Errorf(
			"Received invalid session ID: %v",
			session,
		)
		return
	}

	_, err = messages.SessionMessageToPlaintext(
		&msg,
		c.cipher,
	)
	if err != nil {
		// If we can't decrypt the message, it was most
		// likely forged
		return
	}

	session.remainingBytes = int(msg.Length.Value)
	session.StartData = msg.ExtraData.Value
	return
}

func (c *Client) handleReplyData(canMsg *can.Message) (err error) {
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

	session, ok := c.sessionManager.getSession(msg.SessionId)
	if !ok {
		// Not our session (or possible error)
		// Should we re-transmit in that case?
		err = fmt.Errorf(
			"Received invalid session ID: %v",
			session,
		)
		return
	}

	if session.seq != msg.Seq {
		// Sequence IDs don't match up
		err = fmt.Errorf(
			"Received invalid sequence ID, "+
				"got %v, expected %v",
			msg.Seq,
			session.seq,
		)
		return
	}

	plaintext, err := messages.SessionMessageToPlaintext(
		&msg,
		c.cipher,
	)
	if err != nil {
		// If we can't decrypt the message, it was most
		// likely forged
		return
	}

	dataLength := len(plaintext)
	if dataLength > session.remainingBytes {
		// This shouldn't be happening given the other
		// precautions (message auth checks), but just
		// checking to be save
		err = fmt.Errorf(
			"Payload bigger than expected, "+
				"got %v, expected %v",
			dataLength,
			session.remainingBytes,
		)
		return
	}

	session.addData(plaintext)
	return
}
