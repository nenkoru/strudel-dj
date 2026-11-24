// Imported first: Strudel logs banners with console.log, which would corrupt JSONL on stdout.
console.log = (...a) => console.error(...a);
