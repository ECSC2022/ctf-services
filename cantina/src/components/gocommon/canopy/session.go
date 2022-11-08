package canopy

import (
	"cantina/common/canopy/fields"
	"cantina/common/cipher"
	"fmt"
	"sync"
	"time"
)

const REPLY_TIMEOUT = 6 * time.Second

type sessionManager struct {
	sessions    map[fields.Session]*SessionState
	sessionLock sync.RWMutex
}

func NewSessionManager() (sessionMan *sessionManager) {
	sessionMan = &sessionManager{
		sessions: make(map[fields.Session]*SessionState),
	}
	return
}

func (s *sessionManager) freshSession() (
	sessionId fields.Session,
	session *SessionState,
) {
	var err error

	for {
		sessionId, err = fields.NewSession()
		if err != nil {
			continue
		}

		session = s.createSession(sessionId)
		if session != nil {
			return
		}
	}
}

func (s *sessionManager) storeSession(
	sessionId fields.Session,
	state *SessionState,
) (err error) {
	// Lock from here to function end
	s.sessionLock.Lock()
	defer s.sessionLock.Unlock()

	// Check if a session exists
	if _, ok := s.sessions[sessionId]; ok {
		err = fmt.Errorf(
			"Session %v already exists",
			sessionId,
		)
		return
	}

	s.sessions[sessionId] = state
	return
}

func (s *sessionManager) removeStaleSessions() {
	var outdatedSessions []fields.Session
	for sessionId, state := range s.sessions {
		if state.isTimeout() {
			outdatedSessions = append(
				outdatedSessions,
				sessionId,
			)
		}
	}

	// Lock from here to function end
	s.sessionLock.Lock()
	defer s.sessionLock.Unlock()

	// Delete outdated sessions
	for _, sessionId := range outdatedSessions {
		delete(s.sessions, sessionId)
	}
}

func (s *sessionManager) releaseSession(sessionId fields.Session) {
	// Lock from here to function end
	s.sessionLock.Lock()
	defer s.sessionLock.Unlock()

	// Check if a session exists
	if _, ok := s.sessions[sessionId]; !ok {
		// Session has already been released
		return
	}

	// Remove session
	delete(s.sessions, sessionId)
}

func (s *sessionManager) getSession(sessionId fields.Session) (
	session *SessionState,
	ok bool,
) {
	// Lock from here to function end
	s.sessionLock.RLock()
	defer s.sessionLock.RUnlock()

	session, ok = s.sessions[sessionId]
	return
}

func (s *sessionManager) createSession(sessionId fields.Session) (
	session *SessionState,
) {
	session = nil

	// Lock from here to function end
	s.sessionLock.Lock()
	defer s.sessionLock.Unlock()

	// Check if a session exists
	if _, ok := s.sessions[sessionId]; ok {
		return
	}

	// Create new session storage data
	session = NewSession()
	s.sessions[sessionId] = session
	return
}

type SessionState struct {
	remainingBytes int
	received       chan interface{}
	buffer         []byte
	seq            fields.SequenceNumber
	cipher         *cipher.Cipher
	lastUpdate     time.Time
	StartData      []byte
}

func NewSession() (session *SessionState) {
	session = &SessionState{
		received: make(chan interface{}, 1),
	}
	return
}

func (s *SessionState) SetSessionCipher(cipher *cipher.Cipher) {
	s.cipher = cipher
}

func (s *SessionState) addData(data []byte) {
	s.seq = fields.SequenceNumber{Value: s.seq.Value + 1}
	s.buffer = append(s.buffer, data...)
	s.remainingBytes -= len(data)

	// If we've received all the data, trigger
	// further processing
	if s.remainingBytes <= 0 {
		s.received <- nil
	}
}

func (s *SessionState) receiveNonBlocking() (data []byte) {
	select {
	case _ = <-s.received:
		data = s.buffer
	default:
		data = nil
	}
	return
}

func (s *SessionState) receiveReply() (reply []byte, err error) {
	defer close(s.received)

	select {
	case _ = <-s.received:
		reply = s.buffer
	case <-time.After(REPLY_TIMEOUT):
		err = fmt.Errorf(
			"Ran into timeout while waiting for " +
				"reply from peer",
		)
	}
	return
}

func (s *SessionState) refresh() {
	s.lastUpdate = time.Now()
}

func (s *SessionState) isTimeout() bool {
	now := time.Now()
	return now.Sub(s.lastUpdate) > 2 * time.Second
}
