import Main from "./views/Main.js";
import Menu from "./views/Menu.js";
import Ticket from "./views/Ticket.js";
import Order from "./views/Order.js";

const router = async () => {
    const routes = [
        { path: "/", view: Main },
        { path: "/view-menu", view: Menu },
        { path: "/view-ticket", view: Ticket},
        { path: "/view-order", view: Order }
    ];

    let route = routes.find(route => route.path == location.pathname);
    if (!route) {
        route = routes[0];
    }

    const view = new route.view();
    document.querySelector("#app").innerHTML = await view.getHtml();
}

const navigateTo = url => {
    history.pushState(null, null, url);
    router();
};

document.addEventListener("DOMContentLoaded", () => {
    document.body.addEventListener("click", e => {
        if (e.target.matches("[data-link]")) {
            e.preventDefault();
            navigateTo(e.target.href);
        }
    });

    router();
});

const updateOrderButton = () => {
    const ob = document.getElementById('order-button');
    const items = JSON.parse(localStorage.getItem('order-items'));

    let total = 0;
    let amount = 0;
    for (const i in items) {
        const item = items[i];
        total += item.total;
        amount += item.amount;
    }

    if (amount > 0) {
        ob.text = `Order Now (${amount} items, Total: ${total}C)`
    } else {
        ob.text = `Order Now`;
    }
};

document.addEventListener('click', async e => {
    if (e.target && e.target.className == 'add-item') {
        let items = JSON.parse(localStorage.getItem('order-items'));
        if (items == null) {
            items = [];
            localStorage.setItem('order-items', JSON.stringify(items));
        }

        const itemId = parseInt(e.target.dataset.itemId);
        const price = parseInt(e.target.dataset.price);
        const name = e.target.dataset.name;

        let total = 0;
        for (const i in items) {
            const item = items[i];
            total += item.total;
        }

        if ((total + price) > 30) {
            alert("Can't add to order, hitting credit limit!");
            return;
        }

        let exists = false;
        for (const i in items) {
            let item = items[i];
            if (item.itemId == itemId) {
                item.amount += 1;
                item.total += price;
                exists = true;
                break;
            }
        }

        if (!exists) {
            items.push({
                itemId: itemId,
                name: name,
                amount: 1,
                total: price
            });
        }

        localStorage.setItem('order-items', JSON.stringify(items));
        updateOrderButton();
    } else if (e.target && e.target.id == 'send-order-button') {
        let output = document.getElementById('order-status-info');
        if (output) {
            output.remove();
        }

        let items = JSON.parse(localStorage.getItem('order-items'));
        if (items == null) {
            items = [];
            localStorage.setItem('order-items', JSON.stringify(items));
        }

        // Get order items
        let order_items = [];
        for (const i in items) {
            const item = items[i];
            order_items.push({
                id: item.itemId,
                amount: item.amount
            });
        }

        let table = document.getElementById('table').value;
        let notes = document.getElementById('notes').value;
        let ticket = document.getElementById('ticket').value;

        const order = {
            order_items: order_items,
            table: parseInt(table),
            notes: notes,
            ticket: ticket
        };
        console.log(order);
        
        fetch('/order', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(order)
        }).then(result => {
            if (!result.ok) {
                return result.json().then(r => Promise.reject(r.error));
            }

            return result.json();
        }).then(result => {
            localStorage.clear();

            let pb = document.getElementById('send-order-button');
            pb.outerHTML = `
            <p id="order-status-info">
            Order went through!<br>
            Order-ID: ${result.order_id}<br>
            Auth-Key: ${result.auth_key}<br>
            </p>
            <button id="send-order-button">Send Order</button>
            `;

            updateOrderButton();    
        }).catch(e => {
            let pb = document.getElementById('send-order-button');
            pb.outerHTML = `
            <p id="order-status-info">
            Could not send order: ${e}
            </p>
            <button id="send-order-button">Send Order</button>
            `;
        });
    }
});

window.addEventListener("popstate", router);
updateOrderButton();
