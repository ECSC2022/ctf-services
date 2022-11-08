package tickets

import (
	"cantina/common/structs"
	"crypto/ed25519"
	"errors"
	"fmt"
	"sync"
	"time"

	"github.com/vmihailenco/msgpack/v5"
	"github.com/zekroTJA/timedmap"
)

const TICKET_VALIDSECS = 20 // seconds
const TICKET_VALIDDURATION = TICKET_VALIDSECS * time.Second

type TicketManager struct {
	ticketMap *timedmap.TimedMap
	mapLock sync.RWMutex
	TicketPublicKey []byte
}

func NewManager() (tm *TicketManager) {
	tm = &TicketManager{
		ticketMap:  timedmap.New(1 * time.Second),
	}
	return
}

func (tm *TicketManager) SetPublicKey(
	publicKey []byte,
) {
	k := make([]byte, len(publicKey))
	copy(k, publicKey)
	tm.TicketPublicKey = k
}

func (tm *TicketManager) VerifyTicket(
	ticket []byte,
) (err error) {
	if len(tm.TicketPublicKey) == 0 {
		err = errors.New(
			"Ticket public key missing, try later.",
		)
		return
	}

	// Parse ticket (with signature)
	var ticketSigned structs.TicketSigned
	if err = msgpack.Unmarshal(ticket, &ticketSigned); err != nil {
		err = fmt.Errorf("Couldn't parse ticket: %w", err)
		return
	}

	// Parse wrapped ticket data. We check signature later, so
	// we can do an initial check if we already know the TokenID
	var ticketData structs.Ticket
	err = msgpack.Unmarshal(ticketSigned.TicketData, &ticketData)
	if err != nil {
		err = fmt.Errorf("Couldn't parse ticket: %w", err)
		return
	}

	// Check if token has expired before we check anything else
	timestamp := time.Unix(int64(ticketData.Timestamp), 0)
	expiryTime := timestamp.Add(TICKET_VALIDDURATION)
	now := time.Now()
	if expiryTime.Before(now) {
		err = errors.New("Ticket has already expired.")
		return
	}
	
	// Check if we already have used the token
	// (check this again later, to avoid race conditions)
	tm.mapLock.RLock()
	ticketUsed := tm.ticketMap.Contains(ticketData.TicketId)
	tm.mapLock.RUnlock()
	if ticketUsed {
		err = errors.New("Ticket has already been used.")
		return
	}

	// Verify signature
	signature_valid := ed25519.Verify(
		tm.TicketPublicKey,
		ticketSigned.TicketData,
		ticketSigned.Signature,
	)
	if !signature_valid {
		err = errors.New("Ticket signature invalid.")
		return
	}

	// Get exclusive lock here, so other requests can't
	// update the map. Not sure if this is a valid concern,
	// but there could be a race condition between checking
	// if a ticket has been used and creating a ticket
	tm.mapLock.Lock()
	defer tm.mapLock.Unlock()

	// Check if token has been used (again)
	if tm.ticketMap.Contains(ticketData.TicketId) {
		err = errors.New(
			"Ticket has already been used.",
		)
		return
	}

	// It's an int64 here, but following the check above,
	// this shouldn't be able to be negative
	expiryDuration := expiryTime.Sub(now)

	// Add token to the session state
	tm.ticketMap.Set(
		ticketData.TicketId,
		ticketData.Timestamp,
		expiryDuration,
	)
	
	return
}
