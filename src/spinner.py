import itertools
import sys
import threading
import time


class Spinner:
    """Mostra uma animação no terminal enquanto algo demora. Use com 'with'."""

    def __init__(self, texto: str = "Pensando"):
        self.texto = texto
        self._parar = threading.Event()
        self._thread = threading.Thread(target=self._girar, daemon=True)

    def _girar(self):
        for simbolo in itertools.cycle("|/-\\"):
            if self._parar.is_set():
                break
            sys.stdout.write(f"\r  {simbolo} {self.texto}...")
            sys.stdout.flush()
            time.sleep(0.1)
        # Apaga a linha da animação
        sys.stdout.write("\r" + " " * (len(self.texto) + 10) + "\r")
        sys.stdout.flush()

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *args):
        self._parar.set()
        self._thread.join()