import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(user_data) {
        super(user_data);
        this.setTitle("CANtina: Jukebox - File Upload");
    }

    async cleanupErrors() {
        const errors = document
            .querySelectorAll("article" +
                "[data-view='fup']" +
                "[data-type='error']");
        errors.forEach(e => e.remove());
    }

    async addError(msg) {
        const fup_section = document
            .querySelector("section[data-view='fup']");
        const fup_article = document
            .querySelector("article[data-view='fup']");
        const err_node = document.createElement('article');
        err_node.dataset.view = "fup";
        err_node.dataset.type = "error";
        err_node.innerHTML = `
            <header>
                <h3>Error during file upload.</h3>
            </header>
            <p>
                ${msg}
            </p>
        `;

        fup_section.insertBefore(err_node, fup_article);
    }

    async uploadFile(form) {
        const formData = new FormData(form);
        try {
            let result = await fetch('/file/upload', {
                method: 'POST',
                body: formData
            });

            console.log(result.status);

            // Parse response data
            if (result.status == 200) {
                const data = await result.json();
                const filename = data.filename;
                const file_id = data.file_info[0];
                const track = data.file_info[3];
                const game = data.file_info[4];
                const composer = data.file_info[5];

                const fup_article = document
                    .querySelector("article[data-view='fup']");
                fup_article.innerHTML = `
                    <header>
                        <h3>File uploaded successfully.</h3>
                    </header>
                    <p>
                        <strong>Filename:</strong> ${filename}<br>
                        <strong>File-ID:</strong> ${file_id}<br>
                        <strong>Track:</strong> ${track}<br>
                        <strong>Game:</strong> ${game}<br>
                        <strong>Composer:</strong> ${composer}<br>
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
            .querySelector("form[data-view='fup']");
        form.onsubmit = submit => {
            submit.preventDefault();
            this.cleanupErrors();
            this.uploadFile(form);
        };
    }

    async getHtml() {
        return `
            <section data-view="fup">
                <h2>Upload File</h2>
                <article data-view="fup">
                    <form data-view="fup">
                        <label for="file">
                            Upload <code>*.vgm</code>/<code>*.vgz</code> File. 
                            <input
                                type="file"
                                name="file"
                                accept=".vgm,.vgz"
                                required>
                        </label>
                        <button type="submit">Upload</button>
                    </form>
                </article>
            </section>
        `;
    }
}
