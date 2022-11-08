import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(user_data) {
        super(user_data);
        this.setTitle("CANtina: Jukebox - Login");
    }

    async cleanupErrors() {
        const errors = document
            .querySelectorAll("article" +
                "[data-view='login']" +
                "[data-type='error']");
        errors.forEach(e => e.remove());
    }

    async addError(msg) {
        const login_section = document
            .querySelector("section[data-view='login']");
        const login_article = document
            .querySelector("article[data-view='login']");
        const err_node = document.createElement('article');
        err_node.dataset.view = "login";
        err_node.dataset.type = "error";
        err_node.innerHTML = `
            <header>
                <h3>Error during login.</h3>
            </header>
            <p>
                ${msg}
            </p>
        `;

        login_section.insertBefore(err_node, login_article);
    }

    async loginUser(form) {
        const formData = new FormData(form);
        const data = JSON.stringify(Object.fromEntries(formData));
        try {
            let result = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: data
            });

            // Parse response data
            if (result.status == 200) {
                const login_article = document
                    .querySelector("article[data-view='login']");
                login_article.innerHTML = `
                    <h3>User successfully logged in.</h3>
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
            .querySelector("form[data-view='login']");
        form.onsubmit = submit => {
            submit.preventDefault();
            this.cleanupErrors();
            this.loginUser(form);
        };
    }

    async getHtml() {
        return `
            <section data-view="login">
                <h2>Login</h2>
                <article data-view="login">
                    <form data-view="login">
                        <label for="username">
                            Username
                            <input
                                type="text"
                                name="User"
                                placeholder="e.g. N3fBgjuo3pQstKalyURv"
                                required>
                        </label>
                        <label for="token">
                            Auth-Token 
                            <input
                                type="text"
                                name="Token"
                                placeholder="The authentication token you received after the registration"
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
                        <button type="submit">Login</button>
                    </form>
                </article>
            </section>
        `;
    }
}
