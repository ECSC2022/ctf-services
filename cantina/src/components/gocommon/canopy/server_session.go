package canopy

import (
	"cantina/common/can"
	"cantina/common/canopy/fields"
	"sync"
	"time"
)

const SESSION_TIMEOUT = 6 * time.Second

type ServerSessionManager struct {
	sessions    map[fields.Session]*ServerSession
	sessionLock sync.RWMutex
}

type ServerSession struct {
	SessionChannel chan *can.Message
	LastUpdate time.Time
	channelOpen bool
	channelLock sync.RWMutex
}

func NewServerSessionManager() (sessionMan *ServerSessionManager) {
	sessionMan = &ServerSessionManager{
		sessions: make(map[fields.Session]*ServerSession),
	}
	return
}

func (s *ServerSessionManager) getSession(
	sessionId fields.Session,
) (session *ServerSession, isNew bool) {
	// Lock from here to function end
	s.sessionLock.Lock()
	defer s.sessionLock.Unlock()

	// Check if a session exists
	if sess, ok := s.sessions[sessionId]; ok {
		session = sess
		isNew = false
		return
	}

	session = new(ServerSession)
	session.SessionChannel = make(chan *can.Message, 20)
	session.channelOpen = true
	isNew = true
	s.sessions[sessionId] = session
	return
}

func (s *ServerSessionManager) staleSessions() []fields.Session {
	// Lock from here to function end
	s.sessionLock.RLock()
	defer s.sessionLock.RUnlock()

	var outdatedSessions []fields.Session
	for sessionId, state := range s.sessions {
		if state.isTimeout() {
			outdatedSessions = append(
				outdatedSessions,
				sessionId,
			)
		}
	}

	return outdatedSessions
}

func (s *ServerSessionManager) removeStaleSessions() {
	outdatedSessions := s.staleSessions()

	// Lock from here to function end
	s.sessionLock.Lock()
	defer s.sessionLock.Unlock()

	// Delete outdated sessions
	for _, sessionId := range outdatedSessions {
		session, ok := s.sessions[sessionId]
		if !ok {
			continue
		}

		delete(s.sessions, sessionId)
		go func() {
			defer func() { recover(); }();

			session.channelLock.Lock()
			defer session.channelLock.Unlock()

			session.channelOpen = false
			close(session.SessionChannel);
		}()
	}
}

func (s *ServerSession) SendMessage(msg *can.Message) {
	s.refresh()

	s.channelLock.Lock()
	defer s.channelLock.Unlock()

	if s.channelOpen {
		select {
		case s.SessionChannel<- msg:
			return
		case <-time.After(2 * time.Second):
			return
		}
	}
}

func (s *ServerSession) refresh() {
	s.LastUpdate = time.Now()
}

func (s *ServerSession) isTimeout() bool {
	now := time.Now()
	return now.Sub(s.LastUpdate) > 2 * time.Second
}
