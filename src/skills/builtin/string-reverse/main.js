const readline = require('readline');

let input = '';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', (line) => {
  input += line;
});

rl.on('close', () => {
  try {
    const params = JSON.parse(input);
    const text = params.text || '';
    const reversed = text.split('').reverse().join('');
    console.log(reversed);
  } catch (e) {
    console.error('Error:', e.message);
    process.exit(1);
  }
});