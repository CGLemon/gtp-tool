# https://en.wikipedia.org/wiki/Elo_rating_system

class Elo:
    def __init__(self, rating, k=16.):
        self.set(rating)
        self.set_k(k)

    def get(self):
        return self._rating

    def set(self, rating):
        self._rating = float(rating)

    def get_k(self):
        return self._k;

    def set_k(self, k):
        self._k = max(float(k), 0.)

    def calc(self, opp):
        def calc_winrate(a, b):
            x = (b - a) / 400.0
            return 1.0 / (1.0 + pow(10.0, x))
        return calc_winrate(self._rating, opp._rating)

    def beat(self, opp):
        self.update(opp, 1)

    def draw(self, opp):
        self.update(opp, 0.5)

    def update(self, opp, result):
        winrate = self.calc(opp)
        self._update_rating(result - winrate)
        opp._update_rating(winrate - result)

    def _update_rating(self, diff):
        self._rating = self._rating + self._k * diff

    def __str__(self):
        return str(round(self._rating))

if __name__ == '__main__':
    A = Elo(1000, 16)
    B = Elo(742, 0)
    print(A.calc(B))

    A.beat(B, 1)
    print(A)
    print(B)
