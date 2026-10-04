from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HeuristicTheory:
    """Educational description kept in step with one scheduling implementation."""

    formula: str
    symbols: str
    procedure: str
    example_order: tuple[str, ...]
    example_sto: float
    complexity: str
    use_when: str
    limitation: str
    pseudocode: tuple[str, ...]

    @property
    def example(self) -> str:
        order = " -> ".join(self.example_order)
        return f"Dla J1(6,10), J2(4,11), J3(2,8), J4(7,18): {order}; STO={self.example_sto:g}."

    def details(self, label: str, description: str) -> tuple[str, ...]:
        return (
            "Dane przykładu to cztery zlecenia J1-J4. Para (p,d) oznacza czas obróbki p i termin d.",
            f"Wskaźnik lub cel metody {label}: {self.formula} Oznaczenia: {self.symbols}",
            f"Reguła: {description} {self.procedure}",
            f"Kolejka startowa albo wybrany kandydat. {self.example}",
            "Symulator przypisuje kolejne operacje do dostępnych maszyn i uwzględnia gotowość komponentów.",
            "Dla zlecenia j liczymy C_j, czyli godzinę zakończenia ostatniej wymaganej operacji.",
            "Spóźnienie ma postać T_j=max(0,C_j-d_j). Wykonanie przed terminem nie daje ujemnej kary. "
            "STO to suma dodatnich opoznien dla wszystkich zlecen.",
            f"Wynik przykładu: {self.example} Mniejszy wynik celu ma pierwszeństwo.",
            f"Jak metoda szuka poprawy: {self.procedure}",
            f"Koszt obliczeń: {self.complexity}",
            f"Kiedy warto użyć: {self.use_when}",
            f"Ograniczenie: {self.limitation}",
        )


BASE_ORDER = ("J1", "J3", "J2", "J4")
EDD_ORDER = ("J3", "J1", "J2", "J4")
SPT_ORDER = ("J3", "J2", "J1", "J4")
LPT_ORDER = ("J4", "J1", "J2", "J3")


HEURISTIC_THEORY: dict[str, HeuristicTheory] = {
    "MT": HeuristicTheory(
        formula="klucz(j)=(d_j,p_j,id_j), rosnąco.",
        symbols="d_j termin, p_j czas obróbki.",
        procedure="Najbliższy termin wygrywa; czas i identyfikator rozstrzygają remis.",
        example_order=EDD_ORDER,
        example_sto=2,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="termin klienta jest najważniejszy i potrzebna jest szybka, stabilna reguła.",
        limitation="EDD nie patrzy bezpośrednio na długość kolejnych zleceń ani ryzyko awarii.",
        pseudocode=(
            "jobs = sort(jobs, key=(due_date, processing_time, id))",
            "schedule = evaluate(jobs, machines)",
            "return schedule",
        ),
    ),
    "MO": HeuristicTheory(
        formula="klucz(j)=(p_j,d_j,id_j), rosnąco.",
        symbols="p_j czas obróbki, d_j termin.",
        procedure="Najkrótsze operacje trafiają na początek i szybciej zwalniają kolejkę.",
        example_order=SPT_ORDER,
        example_sto=3,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="liczy się szybki przepływ wielu krótkich zleceń i mały średni czas oczekiwania.",
        limitation="długie lub pilne zlecenie może zostać przesunięte zbyt daleko.",
        pseudocode=(
            "jobs = sort(jobs, key=(processing_time, due_date, id))",
            "schedule = evaluate(jobs, machines)",
            "return schedule",
        ),
    ),
    "MZO": HeuristicTheory(
        formula="klucz(j)=(-p_j,d_j,id_j), rosnąco.",
        symbols="-p_j oznacza sortowanie czasu malejąco.",
        procedure="Najdłuższe operacje są uruchamiane najpierw.",
        example_order=LPT_ORDER,
        example_sto=20,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="długie zadania nie powinny zostać na końcu lub trzeba wcześnie obciążyć zasoby.",
        limitation="dla celu STO długie zadania na początku często opóźniają wiele krótkich zleceń.",
        pseudocode=(
            "jobs = sort(jobs, key=(-processing_time, due_date, id))",
            "schedule = evaluate(jobs, machines)",
            "return schedule",
        ),
    ),
    "MOPT": HeuristicTheory(
        formula="π*=arg min_π key(evaluate(π)); domyślnie najpierw STO, potem odpad i makespan.",
        symbols="π permutacja zleceń, key leksykograficzny cel porównania.",
        procedure="Do 8 zleceń sprawdza wszystkie permutacje; w prostym wariancie do 18 używa programowania dynamicznego, a większe problemy deleguje do Random Restart.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="pełne szukanie O(n!); DP O(n·2^n); dla większych danych heurystyka zastępcza.",
        use_when="potrzebny jest punkt odniesienia lub potwierdzone optimum dla małej kolejki.",
        limitation="nazwa MOPT nie oznacza pełnego przeglądu dla dużych lub złożonych kolejek.",
        pseudocode=(
            "if n <= 8: return min(permutations(jobs), key=evaluation_key)",
            "if simple_case and n <= 18: return dynamic_programming(jobs)",
            "return random_restart(jobs)",
        ),
    ),
    "GENETIC": HeuristicTheory(
        formula="π*=arg min_{π w populacji} key(evaluate(π)).",
        symbols="populacja to zbiór kolejek, mutacja zamienia dwa zlecenia.",
        procedure="Zachowuje najlepszą część populacji i tworzy nowe kolejki przez deterministyczne mutacje; do 8 zleceń używa pełnego przeglądu.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="około O(G·P·E(n)); domyślnie 40 pokoleń i 30 kolejek, mniej dla n>60.",
        use_when="przestrzeń kolejek jest za duża na pełny przegląd, ale warto sprawdzić wiele wariantów.",
        limitation="wynik jest najlepszym znalezionym kandydatem, a nie dowodem optimum dla dużych danych.",
        pseudocode=(
            "population = [EDD, SPT, LPT, input] + random_orders",
            "repeat generations: survivors = best_third(population)",
            "population = survivors + swap_mutations(survivors)",
            "return best(population, key=evaluation_key)",
        ),
    ),
    "SLACK": HeuristicTheory(
        formula="slack_j=d_j-p_j; sortuj rosnąco po (slack_j,d_j,id_j).",
        symbols="slack_j to statyczny zapas czasu liczony dla chwili 0.",
        procedure="Najpierw idzie zlecenie z najmniejszym zapasem między czasem wykonania i terminem.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="trzeba szybko wskazać zlecenia mające najmniejszy bufor bezpieczeństwa.",
        limitation="implementacja liczy zapas raz, bez dynamicznego odejmowania bieżącego czasu.",
        pseudocode=(
            "score[j] = due_date[j] - processing_time[j]",
            "jobs = sort(jobs, key=(score, due_date, id))",
            "return jobs",
        ),
    ),
    "CR": HeuristicTheory(
        formula="CR_j=d_j/max(p_j,ε); sortuj rosnąco.",
        symbols="ε=10^-9 chroni przed dzieleniem przez zero.",
        procedure="Mała relacja terminu do czasu obróbki oznacza większą krytyczność.",
        example_order=("J1", "J4", "J2", "J3"),
        example_sto=17,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="termin trzeba odnieść do rozmiaru samego zlecenia.",
        limitation="jest to statyczny wariant d/p, a nie dynamiczne (d-t)/p przeliczane po każdej operacji.",
        pseudocode=(
            "score[j] = due_date[j] / max(processing_time[j], 1e-9)",
            "jobs = sort(jobs, key=(score, due_date, id))",
            "return jobs",
        ),
    ),
    "EDD_SPT": HeuristicTheory(
        formula="klucz(j)=(d_j,p_j,id_j).",
        symbols="EDD jest kryterium głównym, SPT rozstrzyga jednakowy termin.",
        procedure="Najpierw porównuje terminy, a przy remisie wybiera krótsze zlecenie.",
        example_order=EDD_ORDER,
        example_sto=2,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="termin ma pierwszeństwo, ale remisy powinny szybciej odblokowywać kolejkę.",
        limitation="w aktualnym silniku jest to dokładnie ten sam porządek co MT/EDD.",
        pseudocode=(
            "jobs = sort(jobs, key=(due_date, processing_time, id))",
            "return evaluate(jobs)",
        ),
    ),
    "SPT_EDD": HeuristicTheory(
        formula="klucz(j)=(p_j,d_j,id_j).",
        symbols="SPT jest kryterium głównym, EDD rozstrzyga jednakowy czas.",
        procedure="Najpierw porównuje czasy, a przy remisie wybiera wcześniejszy termin.",
        example_order=SPT_ORDER,
        example_sto=3,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="krótkie zadania mają pierwszeństwo, ale remisy powinny pilnować terminu.",
        limitation="w aktualnym silniku jest to dokładnie ten sam porządek co MO/SPT.",
        pseudocode=(
            "jobs = sort(jobs, key=(processing_time, due_date, id))",
            "return evaluate(jobs)",
        ),
    ),
    "LPT_EDD": HeuristicTheory(
        formula="klucz(j)=(-p_j,d_j,id_j).",
        symbols="LPT jest kryterium głównym, EDD rozstrzyga jednakowy czas.",
        procedure="Najpierw porównuje czasy malejąco, a przy remisie wcześniejszy termin.",
        example_order=LPT_ORDER,
        example_sto=20,
        complexity="sortowanie O(n log n), potem symulacja harmonogramu.",
        use_when="najdłuższe operacje mają zostać uruchomione wcześnie.",
        limitation="w aktualnym silniku jest to dokładnie ten sam porządek co MZO/LPT.",
        pseudocode=(
            "jobs = sort(jobs, key=(-processing_time, due_date, id))",
            "return evaluate(jobs)",
        ),
    ),
    "NEH": HeuristicTheory(
        formula="π_k=arg min_{wstawek pozycji 0..k} key(evaluate(π_{k-1}+j_k)).",
        symbols="j_k są rozpatrywane od największego p_j.",
        procedure="Dodaje po jednym zleceniu i wybiera najlepsze miejsce w aktualnej części kolejki; dla n>60 przechodzi do Local Search.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="około O(n²·E(n)); ograniczony wariant dla ponad 60 zleceń.",
        use_when="potrzebna jest konstrukcyjna heurystyka silniejsza od pojedynczego sortowania.",
        limitation="to wariant NEH dopasowany do celu AOA, a nie klasyczny dowód optymalności flow-shop.",
        pseudocode=(
            "remaining = sort(jobs, key=(-processing_time, due_date, id))",
            "sequence = []",
            "for job in remaining: sequence = best_insertion(sequence, job)",
            "return sequence",
        ),
    ),
    "LOCAL_SEARCH": HeuristicTheory(
        formula="zamień π_i z π_{i+1}, gdy key(π')<key(π).",
        symbols="π' to sąsiedni wariant aktualnej kolejki.",
        procedure="Startuje od EDD i wykonuje poprawiające zamiany sąsiadów aż do lokalnego minimum; duże kolejki mają limit przejść.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="najczęściej O(P·n·E(n)); dla n>40 maksymalnie 2 przejścia i do 24 pozycji.",
        use_when="szybka reguła bazowa jest prawie dobra i wymaga lokalnej korekty.",
        limitation="nie akceptuje chwilowego pogorszenia, więc może zatrzymać się w lokalnym minimum.",
        pseudocode=(
            "best = EDD(jobs)",
            "repeat: try every adjacent swap",
            "if evaluation_key(candidate) < evaluation_key(best): accept(candidate)",
            "until no improvement or pass_limit",
        ),
    ),
    "RANDOM_RESTART": HeuristicTheory(
        formula="π*=min({EDD,SPT,LPT,SLACK} ∪ LS(shuffle_s), key=evaluate).",
        symbols="s to numer restartu, LS to Local Search.",
        procedure="Losuje wiele kolejek stałym ziarnem 123, poprawia każdą lokalnie i zachowuje najlepszą.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="O(R·koszt Local Search); domyślnie R=80, automatycznie mniej dla dużych n.",
        use_when="lokalne minimum zależy od startu i można poświęcić więcej czasu na szukanie.",
        limitation="stałe ziarno daje powtarzalność, ale liczba restartów nadal ogranicza przeszukaną przestrzeń.",
        pseudocode=(
            "best = best_of(EDD, SPT, LPT, SLACK)",
            "for s in range(restarts):",
            "    candidate = local_search(shuffle(jobs, seed=123))",
            "    best = min(best, candidate, key=evaluation_key)",
        ),
    ),
    "ECO_WASTE": HeuristicTheory(
        formula="π*=min(LS(seed_k), key celu); seed grupuje material i kształt.",
        symbols="key może zaczynać od odpadu, STO, makespan albo wyniku zbalansowanego.",
        procedure="Porównuje ziarna materiał/kształt, EDD, SPT i gotowość komponentów, a następnie poprawia je lokalnie.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="kilka sortowań O(n log n) plus Local Search dla maksymalnie czterech ziaren.",
        use_when="zmiany materiału lub kształtu generują odpad i przezbrojenia.",
        limitation="efekt ekologiczny wymaga poprawnych pól materiału, kształtu i odpadu w danych wejściowych.",
        pseudocode=(
            "seeds = [group_by(material, shape), EDD, SPT, group_by(ready, material, shape)]",
            "refined = [local_search(seed, objective) for seed in seeds]",
            "return min(refined, key=evaluation_key)",
        ),
    ),
    "COMPONENT_READY_EDD": HeuristicTheory(
        formula="klucz ziarna=(R_j,d_j,p_j,w_j,id_j); UNSCHEDULABLE na końcu.",
        symbols="R_j gotowość ostatniego komponentu, w_j odpad.",
        procedure="Rezerwuje dostępne partie FIFO, buduje kilka kolejek wykonalnych i poprawia je lokalnie; niewykonalnych zleceń nie ukrywa.",
        example_order=BASE_ORDER,
        example_sto=2,
        complexity="rezerwacja i sortowanie plus Local Search dla czterech ziaren.",
        use_when="plan ma respektować BOM, stany magazynowe i potwierdzone przyszłe dostawy.",
        limitation="wynik zależy od kompletności BOM, stanów, dat dostaw oraz jednostek materiałowych.",
        pseudocode=(
            "feasible, impossible = reserve_components_fifo(jobs, inventory)",
            "seeds = [sort(feasible, key=(ready, due, p, waste)), EDD, material_groups, SPT]",
            "best = min(local_search(seed) for seed in seeds)",
            "return best + sort(impossible, key=(due, id))",
        ),
    ),
    "ROBUST_MC": HeuristicTheory(
        formula="risk=E[M]+α·max(0,P90(M)-E[M]); N~Poisson(p/MTBF), α=0.5.",
        symbols="M makespan, N liczba awarii, MTTR średni czas naprawy.",
        procedure="Ocenia unikalne kolejki z dziewięciu heurystyk w 1000 powtarzalnych scenariuszach awarii i wybiera najlepszy wynik odporny na ryzyko.",
        example_order=EDD_ORDER,
        example_sto=2,
        complexity="około O(K·I·E(n)); K kandydatów, I=1000 scenariuszy.",
        use_when="średni plan nie wystarcza i trzeba zobaczyć przestoje, P90/P95 oraz ryzyko po przezbrojeniu.",
        limitation="awarie maszyn są niezależne; wiarygodność wyniku zależy od realnych MTBF, MTTR i ryzyka po przezbrojeniu.",
        pseudocode=(
            "candidates = unique(EDD, SPT, LPT, SLACK, CR, NEH, LS, ECO, COMPONENT_READY)",
            "for queue in candidates: runs = simulate(queue, iterations=1000, seed=42)",
            "risk = mean_makespan + 0.5 * max(0, p90_makespan - mean_makespan)",
            "return min(candidates, key=(objective_metrics, risk))",
        ),
    ),
}


def theory_for_heuristic(name: str) -> HeuristicTheory | None:
    return HEURISTIC_THEORY.get(name)
