import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor() {
        super();
        this.setTitle("CANtina");
    }

    async getHtml() {
        return `
            <main class="container">
              <div class="grid"><div>
              <figure>
                <img src="assets/cantina.jpg" alt="A dystopian cantina"></img>
              </figure>
              </div><div>
                <h1>Welcome to the CANtina!</h1>
                <p>
                    In this place, nobody has to leave hungry. The food is almost 
                    "free", but you have to put some work in.  Order what you want 
                    and when you check out, complete a proof-of-work. We trade your
                    work  for all kinds of things we need to keep the organisation 
                    running.
                </p>
                <p>
                    If there's something that is not to your liking, better keep
                    it to yourself. But if you really want to take it up with the 
                    cook, be my guest. Just leave him a note. But you saw the guy,
                    right? We don't keep him around for his cooking skills.
                </p>
                <p>
                    To access and use most of our service, you need a ticket. use the 
                    "Get Tickets" menu to generate proof-of-work tickets
                    for other terminals around the CANtina.
                    And when you're done with your food, stay a while and listen
                    to the sounds of the jukebox playing in the background... 
                </p>
              </div></div>
            </main>
        `;
    }
}
