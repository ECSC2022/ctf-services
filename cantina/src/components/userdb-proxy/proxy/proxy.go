package proxy

import (
	"bytes"
	"cantina/common/canopy"
	"cantina/common/canopy/fields"
	"cantina/common/cipher"
	"cantina/user-db/udb"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
)

type Request struct {
	Path string
	Body string
	Key  string
}

type ProxyReplyBuilder struct {
	Env          *udb.Env
	httpc        *http.Client
	auth         bool
	Remoteaccess bool
}

func NewProxyReplyBuilder(env *udb.Env, auth bool) (repbuild *ProxyReplyBuilder, err error) {

	//httpc := http.Client{
	//	Transport: &http.Transport{
	//		DialContext: func(_ context.Context, _, _ string) (net.Conn, error) {
	//			return net.Dial("unix", path.Join(env.DataDir, "userdb.sock"))
	//		},
	//	},
	//}
	httpc := http.Client{}

	repbuild = &ProxyReplyBuilder{
		Env:   env,
		httpc: &httpc,
		auth:  auth,
	}
	return
}

func (p *ProxyReplyBuilder) BuildReply(
	sessionId fields.Session,
	message []byte,
	state *canopy.SessionState,
) []byte {

	p.Env.Log.Println("Handling new Request")
	var reqdata Request
	err := json.Unmarshal(message, &reqdata)
	if err != nil {
		p.Env.Log.Println(err)
		return []byte("Error in Request: " + err.Error())
	}
	var req *http.Request

	//baseUrl, err := url.Parse("http://unix")
	baseUrl, err := url.Parse("http://localhost:10026")
	if err != nil {
		fmt.Println("Malformed URL: ", err.Error())
		return []byte("Error in Request: " + err.Error())
	}
	baseUrl.Path += reqdata.Path

	if len(reqdata.Body) == 0 {
		req, err = http.NewRequest("GET", baseUrl.String(), nil)
	} else {
		req, err = http.NewRequest("POST", baseUrl.String(), strings.NewReader(reqdata.Body))
		req.Header.Set("Content-Type", "application/json; charset=UTF-8")
	}

	username := bytes.Split(state.StartData[:], []byte{0})[0]
	if len(username) > 0 {
		req.Header.Set("User", string(username))
	}

	if p.auth {
		req.Header.Set("Authorization", "yes")
	}

	if p.Remoteaccess {
		username := bytes.Split(state.StartData[:], []byte{0})[0]
		req.Header.Set("AuthenticatedUser", string(username))
	}

	if len(reqdata.Key) > 0 {
		req.Header.Set("Key", reqdata.Key)
	}

	var resp *http.Response
	resp, err = p.httpc.Do(req)
	if err != nil {
		p.Env.Log.Println("Error from server: ", err)
		return []byte("Error in Request: " + err.Error())
	}
	defer resp.Body.Close()

	js, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Fatalln(err)
	}
	p.Env.Log.Println("Send Response")
	return js
}

type ProxySessionInitializer struct {
	Env   *udb.Env
	httpc *http.Client
	auth  bool
}

func NewProxySessionInitializer(env *udb.Env) (repbuild *ProxySessionInitializer, err error) {

	//httpc := http.Client{
	//	Transport: &http.Transport{
	//		DialContext: func(_ context.Context, _, _ string) (net.Conn, error) {
	//			return net.Dial("unix", path.Join(env.DataDir, "userdb.sock"))
	//		},
	//	},
	//}
	httpc := http.Client{}

	repbuild = &ProxySessionInitializer{
		Env:   env,
		httpc: &httpc,
	}
	return
}

func (p *ProxySessionInitializer) InitializeSession(
	sessionId fields.Session,
	state *canopy.SessionState,
) {
	p.Env.Log.Println("Handling User Session")
	state.SetSessionCipher(p.Env.SymmCipher)

	//baseUrl, err := url.Parse("http://unix")
	baseUrl, err := url.Parse("http://localhost:10026")
	if err != nil {
		fmt.Println("Malformed URL: ", err.Error())
		return
	}
	baseUrl.Path = "/proxy/token/"

	username := bytes.Split(state.StartData[:], []byte{0})[0]
	baseUrl.Path += string(username)

	req, err := http.NewRequest("GET", baseUrl.String(), nil)
	if err != nil {
		p.Env.Log.Println("Wrong request format: ", err)
		return
	}

	if p.auth {
		req.Header.Set("Authorization", "yes")
	}

	var resp *http.Response
	resp, err = p.httpc.Do(req)
	if err != nil {
		p.Env.Log.Println("Error from server: ", err)
		return
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		p.Env.Log.Println("Error decoding Object: ", err)
		return
	}

	c := new(cipher.Cipher)
	c.Update(body)
	state.SetSessionCipher(c)
}
