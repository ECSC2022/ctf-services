import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(user_data) {
        super(user_data);
        this.setTitle("CANtina: Jukebox - Register");
    }

    async cleanupErrors() {
        const errors = document
            .querySelectorAll("article" +
                "[data-view='register']" +
                "[data-type='error']");
        errors.forEach(e => e.remove());
    }

    async addError(msg) {
        const register_section = document
            .querySelector("section[data-view='register']");
        const register_article = document
            .querySelector("article[data-view='register']");
        const err_node = document.createElement('article');
        err_node.dataset.view = "register";
        err_node.dataset.type = "error";
        err_node.innerHTML = `
            <header>
                <h3>Error during user creation.</h3>
            </header>
            <p>
                ${msg}
            </p>
        `;

        register_section.insertBefore(err_node, register_article);
    }

    async registerUser(form) {
        const formData = new FormData(form);
        const data = JSON.stringify(Object.fromEntries(formData));
        try {
            let result = await fetch('/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: data
            });

            // Parse response data
            if (result.status == 201) {
                const user_data = await result.json();
                const username = user_data[2];
                const auth_token = user_data[3];
                const register_article = document
                    .querySelector("article[data-view='register']");
                register_article.innerHTML = `
                <header>
                    <h3>User successfully created.</h3>
                </header>
                <p>
                    <strong>Username: </strong>${username}<br>
                    <strong>Auth-Token: </strong>${auth_token}<br>
                </p>
                `;
            } else {
                const error_data = await result.json();
                console.log(error_data);
                this.addError(error_data.message);
            }
        } catch(e) {
            console.log(e);
            this.addError(e);
        }
    }

    async registerEventHandlers() {
        let form = document
            .querySelector("form[data-view='register']");
        form.onsubmit = submit => {
            submit.preventDefault();
            this.cleanupErrors();
            this.registerUser(form);
        };
    }

    async getHtml() {
        return `
            <section data-view="register">
                <h2>Register new user</h2>
                <article data-view="register">
                    <form data-view="register">
                        <label for="username">
                            Username
                            <input
                                type="text"
                                name="User"
                                placeholder="e.g. N3fBgjuo3pQstKalyURv"
                                required>
                        </label>
                        <label for="ticket">
                            Ticket 
                            <input
                                type="text"
                                name="Ticket"
                                placeholder="A ticket retrieved from the CANtina order interface"
                                required>
                        </label>

                        <button type="submit">Register</button>
                    </form>
                </article>
            </section>
        `;
    }
}
