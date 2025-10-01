let balance = 0.0;
let miningRate = 0.000001; // match Python rate
let balanceElement = document.getElementById("balance");

function refreshBalance() {
    balanceElement.innerText = balance.toFixed(8) + " USDT";
}

setInterval(() => {
    balance += miningRate;
    refreshBalance();
}, 1000);
