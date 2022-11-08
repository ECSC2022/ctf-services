import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(user_data) {
        super(user_data);
        this.setTitle("CANtina: Jukebox");
    }

    async getHtml() {
        return `
            <main class="container">
              <div class="grid"><div>
              <figure>
                <img src="assets/jukebox.jpg" alt="A cantina jukebox"></img>
              </figure>
              </div><div>
                <h1>You see, this is the Jukebox I told you about!</h1>
                <p>
                    Doesn't it look great? We love those oldschool systems, 
                    how about you? You can even upload your own music, 
                    and also drop some *notes* while you drop some notes.
                    Totally secure way to share some secrets
                    without having to worry about prying eyes. I told you
                    we made some slight "modifications", didn't I.
                </p>
                <p>
                    But like everythin in here, If you want to use it, you have to work for 
                    it. (Registering and signing in requires a ticket from
                    the main CANtina order terminal.)
                </p>
              </div></div>
            </main>
        `;
    }
}
