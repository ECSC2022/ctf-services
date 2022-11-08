package remoteaccess

import (
	"bytes"
	"cantina/common/canopy"
	"cantina/common/canopy/fields"
	"cantina/jukebox/jukebox"
	"cantina/jukebox/structs"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"regexp"
	"sort"
	"strings"
)

func parseRequest(body []byte, c interface{}) error {
	return json.Unmarshal(body, c)
}

type RemoteAccessReplyBuilder struct {
	Env *jukebox.Env
}

func (p *RemoteAccessReplyBuilder) EnsurePublicKey() (err error) {

	for {
		if len(p.Env.UserTicketManager.TicketPublicKey) != 0 {
			return
		}

		p.Env.Log.Println("Getting signing key")
		repl, err2 := p.Env.UserDbRequest.Send([]byte("{\"Path\": \"/publickey/sign\"}"))
		if err2 != nil {
			p.Env.Log.Println("Key error", err2)
			return
		}
		p.Env.Log.Println("Got key", repl)
		key, _ := base64.StdEncoding.DecodeString(string(repl))
		p.Env.UserTicketManager.SetPublicKey(key)
		break
	}

	return
}

func (p *RemoteAccessReplyBuilder) BuildReply(
	sessionId fields.Session,
	message []byte,
	state *canopy.SessionState,
) []byte {

	p.EnsurePublicKey()

	signed := false
	sr := structs.SignedRequest{}
	decoder := json.NewDecoder(strings.NewReader(string(message)))
	decoder.DisallowUnknownFields()
	err := decoder.Decode(&sr)
	var filereq []byte
	if err != nil {
		filereq = message
	} else {
		signed = true
		filereq, err = base64.StdEncoding.DecodeString(sr.Data)
		if err != nil {
			return []byte("Invalid request: " + err.Error())
		}
	}

	far := structs.FileAccessRequest{}
	decoder = json.NewDecoder(strings.NewReader(string(filereq)))
	decoder.DisallowUnknownFields()
	err = decoder.Decode(&far)
	err = json.Unmarshal([]byte(message), &far)
	if err != nil {
		fmt.Println(string(message))
		return []byte("Invalid request: " + err.Error())
	}

	if signed {
		err = p.Env.UserTicketManager.VerifyTicket(&sr, &far)
		if err != nil {
			return []byte("Invalid request: " + err.Error())
		}
	}
	//data := SignedRequest{}
	fmt.Println("Signed:", signed)
	fmt.Println("Request:", far)

	//var IsAlnum = regexp.MustCompile(`^[a-zA-Z0-9]+$`).MatchString
	var IsAlnum = regexp.MustCompile(`^[a-zA-Z0-9]*$`).MatchString
	var IsMusicName = regexp.MustCompile(`^[a-zA-Z0-9_]+\.vgm$`).MatchString

	switch far.Cmd {
	case "info":
		if len(far.File) > 0 && len(far.Dir) > 0 {

			if !IsMusicName(far.File) {
				return []byte("Invalid filename")
			}
			if !IsAlnum(far.Dir) {
				return []byte("Invalid directory")
			}

			return file_info(&far, signed)
		} else {
			return []byte("Need to provide 'File' and 'Dir' for info")
		}

	case "list":
		if !IsAlnum(far.Dir) {
			return []byte("Invalid directory")
		}
		return []byte(listFiles(far.Dir))
	}

	return []byte("Nothing to see here yet")
}

func file_info(far *structs.FileAccessRequest, signed bool) []byte {
	if signed && (far.User != far.Dir) {
		signed = false
	}

	offset := 2
	if signed {
		offset = 1
	}
	filename := "/data/uploads/" + far.Dir + "/" + far.File
	dat, err := os.ReadFile(filename)
	if err != nil {
		return []byte(err.Error())

	}

	//Read File Info
	result := bytes.Split([]byte(dat), []byte("Gd3 "))
	if len(result) != 2 {
		fmt.Println(result)
		return []byte("Something seems to be wrong with the file")
	}

	entries := bytes.Split([]byte(result[1]), []byte("\x00\x00"))

	var out []byte
	for _, item := range entries[:len(entries)-offset] {
		out = append(out, []byte("\x00\x00")...)
		out = append(out, item...)
	}

	return out

}

func listFiles(dir string) (output string) {

	files, err := ioutil.ReadDir("/data/uploads/" + dir)
	fmt.Println(files)
	if err != nil {
		//log.Fatal(err)
		return
	}

	sort.Slice(files, func(i, j int) bool {
		return files[i].ModTime().After(files[j].ModTime())
	})

	for _, file := range files {
		output += fmt.Sprintf("[%6d] %s", file.Size(), file.Name())
		if len(output) > 512 {
			break
		}
	}
	return
}

func Info() string {

	header := `
       _       _        ____            
      | |     | |      |  _ \           
      | |_   _| | _____| |_) | _____  __
  _   | | | | | |/ / _ \  _ < / _ \ \/ /
 | |__| | |_| |   <  __/ |_) | (_) >  < 
  \____/ \__,_|_|\_\___|____/ \___/_/\_\



Remote access interface.

Expected format for standard Jukebox Messages:
---
{"Cmd": <list | info>, "Dir": <username>, "File": <filename>}
---
For authenticated requests, get a token from the userdb
with the following payload
---
{"Path": "/jukebox/ticketrequest", "Body": "<Jukebox Message>"}
---
and send the signed message here
`

	return header

}
