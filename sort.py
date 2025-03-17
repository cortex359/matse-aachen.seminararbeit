import math
import random

def heapsort(arr, cmp=lambda x, y: x < y):
    """
    Heapsort-Algorithmus.
    Sortiert die Liste a in-place.

    Parameter:
      a   -- zu sortierende Liste
      cmp -- Vergleichsfunktion (Lambda), die zwei Elemente vergleicht.
             Standard: lambda x, y: x < y (natürliche Ordnung).
    """
    a = arr.copy()
    n = len(a)
    # Aufbau des Heaps (max-Heap: größtes Element an der Wurzel)
    for start in range(n // 2 - 1, -1, -1):
        _sift_down_optimized(a, start, n, cmp)
    # Sortieren: Das größte Element wird wiederholt an das Ende verschoben.
    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        _sift_down_optimized(a, 0, end, cmp)

    return a


def _sift_down(a, start, end, cmp):
    """
    Hilfsfunktion für Heapsort.
    „Sift down“ (Absenken) des Elementes an Index start im Heap [0, end).
    """
    root = start
    tmp = a[root]
    child = 2 * root + 1  # linkes Kind
    while child < end:
        # Bestimme das größere Kind (für einen max-Heap)
        right = child + 1
        if right < end and cmp(a[child], a[right]):
            child = right
        # Ist tmp bereits größer oder gleich dem Kind? Falls ja, ist die richtige Position gefunden.
        if not cmp(tmp, a[child]):
            break
        a[root] = a[child]
        root = child
        child = 2 * root + 1
    a[root] = tmp


def _sift_down_optimized(a, start, end, cmp):
    """
    Optimierte Version von _sift_down nach Floyd.
    Zuerst wird das Element an start bis zum Blatt abgesenkt,
    dann wird der korrekte Einfügepunkt auf dem Rückweg gesucht.
    """
    root = start
    tmp = a[root]

    # Phase 1: Absinken bis zum Blatt, ohne tmp in jeder Iteration zu vergleichen.
    child = 2 * root + 1
    while child < end:
        # Wähle das größere Kind:
        if child + 1 < end and cmp(a[child], a[child + 1]):
            child += 1
        # Verschiebe das Kind nach oben:
        a[root] = a[child]
        root = child
        child = 2 * root + 1

    # Phase 2: Auf dem zurückgelegten Pfad den richtigen Platz für tmp finden.
    # Dabei wird entlang der Elternkette rückwärts geprüft.
    insertion_point = root
    parent = (insertion_point - 1) // 2
    while insertion_point > start and cmp(a[parent], tmp):
        a[insertion_point] = a[parent]
        insertion_point = parent
        parent = (insertion_point - 1) // 2
    a[insertion_point] = tmp


def quicksort(arr, cmp=lambda x, y: x < y):
    """
    Quicksort-Algorithmus.
    Sortiert die Liste a in-place.

    Parameter:
      a   -- zu sortierende Liste
      cmp -- Vergleichsfunktion (Lambda), die zwei Elemente vergleicht.
             Standard: lambda x, y: x < y.

    Optimierungen:
      - Median-of-three zur Wahl des Pivot-Elements.
      - Für kleine Teilbereiche (Länge ≤ 10) wird Insertion Sort verwendet.
    """
    a = arr.copy()
    def _quicksort(low, high):
        if high - low > 10:
            mid = (low + high) // 2
            # Median-of-three: sortiere a[low], a[mid] und a[high]
            if cmp(a[mid], a[low]):
                a[low], a[mid] = a[mid], a[low]
            if cmp(a[high], a[low]):
                a[low], a[high] = a[high], a[low]
            if cmp(a[high], a[mid]):
                a[mid], a[high] = a[high], a[mid]
            pivot = a[mid]
            # Verstecke das Pivot-Element: tausche es mit dem vorletzten Element.
            a[mid], a[high - 1] = a[high - 1], a[mid]
            i = low
            j = high - 1
            while True:
                i += 1
                # Solange a[i] kleiner als Pivot ist, weitergehen (mit Grenzwertprüfung)
                while i < high and cmp(a[i], pivot):
                    i += 1
                j -= 1
                # Solange a[j] größer als Pivot ist, weitergehen
                while j > low and cmp(pivot, a[j]):
                    j -= 1
                if i < j:
                    a[i], a[j] = a[j], a[i]
                else:
                    break
            # Bringe das Pivot-Element an seine korrekte Stelle
            a[i], a[high - 1] = a[high - 1], a[i]
            _quicksort(low, i - 1)
            _quicksort(i + 1, high)
        else:
            # Für kleine Bereiche: Insertion Sort
            for i in range(low + 1, high + 1):
                key = a[i]
                j = i - 1
                while j >= low and cmp(key, a[j]):
                    a[j + 1] = a[j]
                    j -= 1
                a[j + 1] = key

    if a:
        _quicksort(0, len(a) - 1)
        return a


def bubble_sort(arr, cmp=lambda x, y: x < y):
    """
    Bubble Sort-Algorithmus.
    Sortiert die Liste a in-place.

    Parameter:
      a   -- zu sortierende Liste
      cmp -- Vergleichsfunktion (Lambda), die zwei Elemente vergleicht.
             Standard: lambda x, y: x < y.

    Optimierung:
      - Abbruch, sobald in einem Durchlauf keine Vertauschungen stattfinden.
    """
    a = arr.copy()
    n = len(a)
    for i in range(n):
        swapped = False
        # Durchlaufe den unsortierten Teil der Liste
        for j in range(1, n - i):
            # Vergleiche benachbarte Elemente; tausche, falls a[j] vor a[j-1] kommen soll.
            if cmp(a[j], a[j - 1]):
                a[j], a[j - 1] = a[j - 1], a[j]
                swapped = True
        if not swapped:
            break
    return a


if __name__ == "__main__":
    global com_count
    com_count = 0

    def cmp_a(x, y):
        global com_count
        com_count += 1
        return x < y

    def cmp_b(A, B):
        #print(f"{A} < {B}") if A < B else print(f"{A} > {B}")
        global le_count, ge_count
        if A < B:
            le_count += 1
        else:
            ge_count += 1

        return A < B


    quick_count = []
    heap_count = []

    for _ in range(1):
        arr = [random.randint(0, 50) for _ in range(35)]
        n = len(arr)

        com_count = 0
        h1 = heapsort(arr, cmp_a)
        print(f"Heapsort:    n={n:3d},     n*log_2(n)= {n*math.log(n, 2):8.2f}, com_count={com_count}")
        heap_count.append(com_count)

        com_count = 0
        q1 = quicksort(arr, cmp_a)
        print(f"Quicksort:   n={n:3d}, 1.39*n*log_2(n)= {1.39*n*math.log(n, 2):8.2f}, com_count={com_count}")
        quick_count.append(com_count)

        com_count = 0
        b1 = bubble_sort(arr, cmp_a)
        #print(f"Bubble Sort: n={n:3d},            n**2= {n**2:8.2f}, com_count={com_count}")

        assert (h1 == q1 == b1)

    print(f"Average Heapsort: {sum(heap_count) / len(heap_count)}")
    print(f"Average Quicksort: {sum(quick_count) / len(quick_count)}")

    print(f'{"-" * 50}')

    global le_count, ge_count
    le_count: int = 0
    ge_count: int = 0

    cp_points = [11, 36, 26, 29, 42, 42, 35, 35, 32, 38, 38, 34, 0, 32, 5, 34, 30, 34, 25, 50, 40, 35, 35, 14, 39, 47, 31, 47, 34, 33, 40, 27, 39, 2, 31]
    cw_points = [0, 20, 8, 13, 14, 20, 20, 19, 15, 20, 19, 6, 4, 20, 0, 18, 20, 19, 7, 20, 19, 15, 9, 2, 9, 20, 10, 20, 6, 6, 7, 9, 13, 0, 17]
    rp_points = [0, 20, 4, 0, 12, 9, 7, 10, 7, 25, 4, 4, 0, 11, 0, 12, 6, 23, 4, 28, 6, 4, 9, 7, 17, 22, 10, 18, 4, 4, 4, 4, 15, 0, 12]
    wr_points = [0, 3, 5, 0, 3, 8, 9, 9, 10, 2, 0, 6, 1, 5, 0, 9, 5, 7, 5, 9, 7, 0, 5, 0, 4, 10, 3, 8, 6, 7, 4, 4, 4, 4, 2]
    iv_points = [i for i in range(1, 36)]

    for points in [cp_points, cw_points, rp_points, wr_points, iv_points]:
        for _ in range(10000):
            random.shuffle(points)
            heapsort(points, cmp_b)

        #print(f'{le_count=}\n{ge_count=}')
        print(ge_count/(le_count + ge_count))