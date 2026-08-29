/** @type {import('next').NextConfig} */
const config = {
  // Znacznik trybu pracy lokalnej rysuje sie NA ekranie i wchodzi do zrzutu,
  // wiec bramka odwzorowania liczylaby go jako roznice wobec ramki. Zdejmujemy
  // go, zeby pomiar mierzyl ekran, a nie narzedzie.
  devIndicators: false,

  // Silnik jest w Pythonie i stoi obok jako funkcje. W czasie pracy lokalnej
  // przekierowujemy wywolania na niego, zeby przegladarka widziala jeden adres.
  async rewrites() {
    return [{ source: "/api/:sciezka*", destination: "http://127.0.0.1:8000/api/:sciezka*" }];
  },
};
export default config;
