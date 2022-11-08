import UnAuth from "./nav/UnAuth.js";
import Auth from "./nav/Auth.js";
import Main from "./views/Main.js";
import Login from "./views/Login.js";
import Register from "./views/Register.js";
import FileUpload from "./views/FileUpload.js";
import FileListing from "./views/FileListing.js";

const router = async () => {
    const routes = [
        {
            path: "/",
            view: Main,
            privileged: false
        },
        {
            path: "/view-register",
            view: Register, 
            privileged: false
        },
        {
            path: "/view-login",
            view: Login,
            privileged: false
        },
        {
            path: "/view-file-upload",
            view: FileUpload,
            privileged: true
        },
        {
            path: "/view-file-list",
            view: FileListing,
            privileged: true
        }
    ];

    let route = routes.find(route => route.path == location.pathname);
    if (!route) {
        route = routes[0];
    }

    // Check if we're logged in
    let user_info = null;
    try {
        let r = await fetch('/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
        });

        if (r.status == 200) {
            const replyData = await r.json();
            user_info = replyData.username;
        }
    } catch (e) {
        console.error(e);
    }

    // If we're privileged, user_info is required
    if (route.privileged && user_info == null) {
        route = routes[0];
    }

    const view = new route.view(user_info);
    document.querySelector("#app").innerHTML = await view.getHtml();
    const nav = user_info == null ?
        new UnAuth(user_info) :
        new Auth(user_info);
    document.querySelector("#nav").innerHTML = await nav.getHtml();
    await view.registerEventHandlers();
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

//const updateOrderButton = () => {
//    const ob = document.getElementById('order-button');
//    const items = JSON.parse(localStorage.getItem('order-items'));
//
//    let total = 0;
//    let amount = 0;
//    for (const i in items) {
//        const item = items[i];
//        total += item.total;
//        amount += item.amount;
//    }
//
//    if (amount > 0) {
//        ob.text = `Order Now (${amount} items, Total: ${total}C)`
//    } else {
//        ob.text = `Order Now`;
//    }
//};

document.addEventListener('click', async e => {
//    if (e.target && e.target.id == 'pow-button') {
//        let output = document.getElementById('ticket-output');
//        if (output) {
//            output.remove();
//        }
//
//        let bt = `
//            <button id="pow-button-prog" aria-busy="true">
//              Calculating proof-of-work...
//            </button>
//        `;
//        e.target.outerHTML = bt;
//
//        PoW()
//            .then(ticket => {
//                let pb = document.getElementById('pow-button-prog');
//                pb.outerHTML = `
//                <article id="ticket-output">
//                Ticket: ${ticket.ticket}
//                </article>
//                <button id="pow-button">Generate Ticket</button>
//                `;
//            })
//            .catch(e => {
//                let pb = document.getElementById('pow-button-prog');
//                pb.outerHTML = `
//                <article id="ticket-output">
//                Could not get ticket, probably timed out.
//                </article>
//                <button id="pow-button">Generate Ticket</button>
//                `;
//                console.log(e);
//            });
//    } else if (e.target && e.target.className == 'add-item') {
//        let items = JSON.parse(localStorage.getItem('order-items'));
//        if (items == null) {
//            items = [];
//            localStorage.setItem('order-items', JSON.stringify(items));
//        }
//
//        const itemId = parseInt(e.target.dataset.itemId);
//        const price = parseInt(e.target.dataset.price);
//        const name = e.target.dataset.name;
//
//        let total = 0;
//        for (const i in items) {
//            const item = items[i];
//            total += item.total;
//        }
//
//        if ((total + price) > 30) {
//            alert("Can't add to order, hitting credit limit!");
//            return;
//        }
//
//        let exists = false;
//        for (const i in items) {
//            let item = items[i];
//            if (item.itemId == itemId) {
//                item.amount += 1;
//                item.total += price;
//                exists = true;
//                break;
//            }
//        }
//
//        if (!exists) {
//            items.push({
//                itemId: itemId,
//                name: name,
//                amount: 1,
//                total: price
//            });
//        }
//
//        localStorage.setItem('order-items', JSON.stringify(items));
//        updateOrderButton();
//    } else if (e.target && e.target.id == 'send-order-button') {
//        let output = document.getElementById('order-status-info');
//        if (output) {
//            output.remove();
//        }
//
//        let bt = `
//            <button id="send-order-button-prog" aria-busy="true">
//              Calculating proof-of-work...
//            </button>
//        `;
//        e.target.outerHTML = bt;
//        let pow = PoW();
//
//        let items = JSON.parse(localStorage.getItem('order-items'));
//        if (items == null) {
//            items = [];
//            localStorage.setItem('order-items', JSON.stringify(items));
//        }
//
//        // Get order items
//        let order_items = [];
//        for (const i in items) {
//            const item = items[i];
//            order_items.push({
//                id: item.itemId,
//                amount: item.amount
//            });
//        }
//
//        // Get table
//        let table = document.getElementById('table').value;
//
//        // Get notes
//        let notes = document.getElementById('notes').value;
//
//        pow.then(ticket => {
//                const order = {
//                    order_items: order_items,
//                    table: parseInt(table),
//                    notes: notes,
//                    ticket: ticket.ticket
//                };
//                console.log(order);
//                
//                fetch('/order', {
//                    method: 'POST',
//                    headers: { 'Content-Type': 'application/json' },
//                    body: JSON.stringify(order)
//                }).then(result => {
//                    if (!result.ok) {
//                        return result.json().then(r => Promise.reject(r.error));
//                    }
//
//                    return result.json();
//                }).then(result => {
//                    localStorage.clear();
//
//                    let pb = document.getElementById('send-order-button-prog');
//                    pb.outerHTML = `
//                    <p id="order-status-info">
//                    Order went through!<br>
//                    Order-ID: ${result.order_id}<br>
//                    Auth-Key: ${result.auth_key}<br>
//                    </p>
//                    <button id="send-order-button">Generate Ticket</button>
//                    `;
//
//                    updateOrderButton();    
//                }).catch(e => {
//                    let pb = document.getElementById('send-order-button-prog');
//                    pb.outerHTML = `
//                    <p id="order-status-info">
//                    Could not send order: ${e}
//                    </p>
//                    <button id="send-order-button">Generate Ticket</button>
//                    `;
//                });
//            })
//            .catch(e => {
//                let pb = document.getElementById('send-order-button-prog');
//                pb.outerHTML = `
//                <p id="order-status-info">
//                Could not get ticket, probably timed out on proof-of-work.
//                </p>
//                <button id="send-order-button">Generate Ticket</button>
//                `;
//                console.log(e);
//            });
//    }
});

window.addEventListener("popstate", router);
//updateOrderButton();
