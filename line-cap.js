const readline = require("readline");

const max = parseInt(process.argv[2] || "20", 10);
let count = 0;

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on("line", (line) => {
  if (count++ < max) {
    console.log(line);
  } else {
    rl.close();
    process.exit(0);
  }
});

rl.on("close", () => {
  process.exit(0);
});

process.stdin.on("end", () => {
  process.exit(0);
});
