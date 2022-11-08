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
            <li><a href="/view-file-list" data-link>List Files</a></li>
            <li><a href="/view-file-upload" data-link>Upload Files</a></li>
            <li>User-Info: ${this.user_info}</li>
        </ul>
        `;
    }
}
