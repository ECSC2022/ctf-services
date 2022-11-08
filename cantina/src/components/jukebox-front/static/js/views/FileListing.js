import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor(user_data) {
        super(user_data);
        this.setTitle("CANtina: Jukebox - File Listing");
    }

    async registerEventHandlers() {
        this.loadFiles();

        const updateButton = document
            .querySelector("button" +
                "[data-view='file-list']" +
                "[data-type='update-button']");
        updateButton.onclick = this.loadFiles;
    }
    
    async loadFiles() {
        try {
            let result = await fetch('/file/list/');
            let data = await result.json();
            let html = data.map(file => {
                let file_id = file[0];
                let file_timestamp = file[1];
                let file_user = file[2];
                let file_track = file[3];
                let file_game = file[4];
                let file_composer = file[5];
                let file_filename = file[6];

                return `
                <details
                  data-view="file-list"
                  data-type="file-details"
                  data-file-id="${file_id}"
                  data-filename="${file_filename}"
                  data-username="${file_user}">
                    <summary>${file_filename} <ins><small>by ${file_user}</small></ins></summary>
                    <blockquote>
                    <ul>
                        <li><strong>File-ID:</strong> ${file_id}</li>
                        <li><strong>Timestamp:</strong> ${file_timestamp}</li>
                        <li><strong>Track:</strong> ${file_track}</li>
                        <li><strong>Game:</strong> ${file_game}</li>
                        <li><strong>Composer:</strong> ${file_composer}</li>
                    </ul>
                    <footer>Base Info</footer>
                    </blockquote>
                    <blockquote data-file-id="${file_id}">
                    No extended info loaded.
                    <footer>Extended Info</footer>
                    </blockquote>
                </details>
                `;
            }).join('')


            const fileList = document
                .querySelector("article" +
                    "[data-view='file-list']" +
                    "[data-type='list']");
            fileList.innerHTML = html; 

            // Load extended info when details are opened
            const fileDetails = document
                .querySelectorAll("details" +
                    "[data-view='file-list']" +
                    "[data-type='file-details']");
            const ownUserName = this.user_data;
            fileDetails.forEach(d => {
                d.ontoggle = _ => {
                    if (d.open) {
                        let user_param = '';
                        if (d.dataset.username !== ownUserName) {
                            user_param = new URLSearchParams({
                                'User': d.dataset.username
                            });
                            user_param = '?' + user_param;
                        }

                        fetch('/file/info/' + d.dataset.filename + user_param)
                            .then(r => r.json())
                            .then(r => {
                                console.log(r);
                                const extended = document
                                    .querySelector(`blockquote[data-file-id='${d.dataset.fileId}']`);
                                extended.innerHTML = `
                                <ul>
                                    <li><strong>Track</strong>: ${r.track}</li>
                                    <li><strong>Track JP</strong>: ${r.track_jp}</li>
                                    <li><strong>Game</strong>: ${r.game}</li>
                                    <li><strong>Game JP</strong>: ${r.game_jp}</li>
                                    <li><strong>System</strong>: ${r.system}</li>
                                    <li><strong>System JP</strong>: ${r.system_jp}</li>
                                    <li><strong>Author</strong>: ${r.author}</li>
                                    <li><strong>Author JP</strong>: ${r.author_jp}</li>
                                    <li><strong>Release Date</strong>: ${r.release_date}</li>
                                    <li><strong>Notes</strong>: ${r.notes}</li>
                                </ul>
                                <footer>Extended Info</footer>
                                `;
                            })
                            .catch(e => console.log(e));
                    }
                };
            });
        } catch(e) {
            console.log(e);
        }
    }

    async getHtml() {
        return `
            <section data-view="file-list">
                <h2>File List</h2>
                <p>
                    The following list contains the most recent uploaded files. To refresh
                    the list, click the update button or refresh the page.
                </p>

                <button data-view="file-list" data-type="update-button">Update List</button>
                <article data-view="file-list" data-type="list">
                    <p>No files available.</p>
                </article>
            </section>
        `;
    }
}
