import AbstractView from "./AbstractView.js";

export default class extends AbstractView {
    constructor() {
        super();
        this.setTitle("CANtina - Order");
    }

    async getHtml() {
        let html = `<section><h2>Complete Your Order</h2></section>`;
        html += `<article><h3>Items</h3>
            <table><thead><tr>
            <th scope="col">Item</th>
            <th scope="col">Amount</th>
            <th scope="col">Price</th>
            </tr></thead><tbody>
        `;

        const items = JSON.parse(localStorage.getItem('order-items'));
        let total = 0;
        for (const i in items) {
            const item = items[i];
            total += item.total;

            html += `<tr>
                <td>${item.name}</td>
                <td>${item.amount}</td>
                <td>${item.total}C</td>
                </tr>
            `;
        }
        html += `</tbody></table>`;

        html += `<label for="table">Table-Number</label>`
        html += `<select id="table" required>`
        for (let i = 1; i < 200; i++) {
            if (i == 1) {
                html += `<option selected="selected" value="${i}">Table ${i}</option>`;
            } else {
                html += `<option value="${i}">Table ${i}</option>`;
            }
        }
        html += `</select>`;

        html += `<label for="notes">Notes <input type="text" id="notes" name="notes" placeholder="Enter some notes for the kitchen" required></label>`;
        html += `<label for="ticket">Ticket <input type="text" id="ticket" name="ticket" placeholder="Ticket acquired through the proof-of-work" required></label>`;

        html += `<strong>Order-Total: ${total}C</strong>`;

        html += `<footer>
            <button id="send-order-button">
              Send Order
            </button></footer>
        `;
        html += `</article>`;
        return html;
    }
}
