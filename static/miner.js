let mining = false;
let mined = 0;

document.getElementById("startBtn").addEventListener("click", () => {
    if (!mining) {
        mining = true;
        document.getElementById("status").innerText = "Mining in progress...";
        mine();
    }
});

function mine() {
    let progress = 0;
    const progressBar = document.getElementById("progressBar");
    const output = document.getElementById("output");

    const interval = setInterval(() => {
        if (progress < 100) {
            progress += 2;
            progressBar.style.width = progress + "%";
        } else {
            clearInterval(interval);
            mined += (Math.random() * 0.05 + 0.01).toFixed(4); // fake mined USDT
            output.innerText = `Mined: ${mined} USDT`;
            document.getElementById("status").innerText = "Mining complete!";
            mining = false;
        }
    }, 150);
}
