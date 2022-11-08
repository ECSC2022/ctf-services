import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor() {
        super();
        this.setTitle("CANtina - Menu");
    }

    async getHtml() {
        const response = await fetch('/items');
        const itemData = await response.json();
        const header = `<section>
        You can pick any items you want from the menu, but you are
        limited to an amount of 30 credits at checkout. For purchasing,
        a proof-of-work will be calculated on checkout, if you need
        a ticket for anything else, you can use the "Get Ticket"
        page.
        </section>
        `;

        const out = itemData.categories.map(category => {
            let html = `<section><h2>${category.name}</h2>`;

            const items = category.items.map(item => {
                let html = `<article>`;
                //html += `<header><h3>${item.name}</h3></header>`;
                html += `
                <figure class="menu-item-image">
                    <img src="assets/img/${item.image_url}"></img>
                    <figcaption>${item.name}</figcaption>
                </figure>
                <p>Price: ${item.price}C</p>
                <button class="add-item" data-item-id="${item.item_id}" data-price="${item.price}" data-name="${item.name}">
                    Add to Order
                </button>
                `;
                html += `</article>`;
                return html;
            });

            for (let i = 0; i < items.length; i += 3) {
                html += `<div class="grid">`;
                for (let j = 0; j < 3; j++) {
                    const index = i + j;
                    if (index >= items.length) {
                        html += `<div></div>`;
                    } else {
                        html += `<div>${items[index]}</div>`;
                    }
                }
                html += `</div>`;
            }

            html += `<section>`;
            return html;
        }).join('');

        return `${header}${out}`;
    }
}
