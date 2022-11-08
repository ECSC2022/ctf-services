export default class {
    constructor(user_info) {
        this.user_info = user_info;
    }

    async getHtml() {
        return `
        <ul>
            <li><a href="/" data-link><strong>CANtina: Jukebox</strong></a></li>
        </ul>
        `;
    }
}
