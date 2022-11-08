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
                <h1>Welcome to the Jukebox!</h1>
                <p>
                    We love oldschool systems, how about you? Try out
                    our Jukebox system. We support the upload of VGM
                    files; you can go ahead and upload your own, or
                    see what others have uploaded.
                </p>
                <p>
                    Registering and signing in requires a ticket from
                    the main CANtina order terminal.
                </p>
              </div></div>
            </main>
        `;
    }
}
