import AbstractNav from "./AbstractNav.js";

export default class extends AbstractNav {
    constructor(user_info) {
        super(user_info);
    }

    async getHtml() {
        const base = await super.getHtml();
        return `
        ${base}
        <ul>
            <li><a href="/view-login" data-link>Login</a></li>
            <li><a href="/view-register" data-link>Register</a></li>
        </ul>
        `;
    }
}
