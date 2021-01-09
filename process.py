from imports import *


class ControlSystem(object):
    def __init__(self,
                 kp: float,
                 A: float,
                 beta: float,
                 h_init: float,
                 h_dest: float,
                 t: float,
                 Tp: float,
                 Ti: float,
                 Td: float,
                 h_min: float,
                 h_max: float,
                 u_min: float,
                 u_max: float,
                 Qd_min: float,
                 Qd_max: float,
                 iteration_limit: int,
                 save_tolerance: float):
        """Klasa przetrzymujący układ automatycznej regulacji UAR
        W tym przypadku UAR zbudowany ze zbiornika z dopływem i odpływem wody,
        wygenerowane dane zwrotne są w "dataframe"


        :param kp: Wzmocnienie Regulatora [-]
        :param A: Pole powierzchi przekroju poprzecznego [m^2]
        :param beta: Współczynnik wypływu [m^{5/2}/s]
        :param h_init: Początkowy poziom substancji [m]
        :param h_dest: Oczekiwany poziom substancji [m]
        :param t: Czas trawnia [s]
        :param Tp: Okres Probkowania [1/s]
        :param Ti: Czas Wyprzedzenia [s]
        :param Td: Czas Zdwojenia [s]
        :param h_min: Minimalny poziom substancji [m]
        :param h_max: Maksymalny poziom substancji [m]
        :param u_min: Minimalna wielkość sterująca [V]
        :param u_max: Maksymalne wielkość sterująca [V]
        :param Qd_min: Minimalne Natężenie dopływu [m^3/s]
        :param Qd_max: Maksymalne Natężenie dopływu [m^3/s]
        :param iteration_limit: Limit iteracji
        :param save_tolerance: Tolerancja zapisu odczytu
        """
        # Dummy Variables
        self.dataframe: pd.DataFrame = pd.DataFrame()

        # Data Initialization
        self.__kp: float = kp
        self.__A: float = A
        self.__beta: float = beta
        self.__h_initial: float = h_init
        self.__h_dest: float = h_dest
        self.__t: float = t
        self.__Tp: float = Tp
        self.__Ti: float = Ti
        self.__Td: float = Td
        self.__h_min: float = h_min
        self.__h_max: float = h_max
        self.__u_min: float = u_min
        self.__u_max: float = u_max
        self.__Qd_min: float = Qd_min
        self.__Qd_max: float = Qd_max

        # Computed Data
        self.__data: Dict[str, List[float]] = {
            "t": [0], "h": [h_init], "e": [0], "u": [0], "Qd": [0], "Qo": [0]
        }

        self.__helpers: Dict[str, float] = {
            "Tp/Ti": self.__Tp / self.__Ti or 0, "Td/Tp": self.__Td / self.__Ti or 0, "sum_e": 0,
            "Tp/A": self.__Tp / self.__A or 0, "Qd_lim/u_lim": (Qd_max - Qd_min) / (u_max - u_min) or 0,
            "previous_save": h_init,
        }

        self.__iteration: int = 0
        self.__iteration_limit: int = iteration_limit
        self.__save_tolerance: float = save_tolerance

        self.__remaining_cycles: int = int(self.__t / self.__Tp)

        # Calculate Data
        self.__init_control_flow()
        self.__finalize_data()

    def __init_control_flow(self):
        while True:
            self.__process_step()
            self.__iteration += 1
            if self.__should_terminate(): break

    def __process_step(self):
        self.__data["e"].append(self.__find_control_difference())
        self.__data["t"].append(self.__iteration)
        self.__helpers["sum_e"] += self.__data["e"][-1]

        self.__data["u"].append(self.__find_steer())
        self.__data["Qd"].append(self.__find_intake())
        self.__data["Qo"].append(self.__find_output())
        self.__data["h"].append(self.__quantitize_substance())

    def __find_control_difference(self) -> float:
        return self.__h_dest - self.__data["h"][-1]

    def __find_steer(self) -> float:
        return max(self.__u_min, min(self.__u_max,
                                     self.__kp
                                     * (self.__data["e"][-1]
                                        + self.__helpers["Tp/Ti"] * self.__helpers["sum_e"]
                                        + self.__helpers["Td/Tp"] * (self.__data["e"][-1] - self.__data["e"][-2]))))

    def __find_intake(self) -> float:
        return self.__data["u"][-1] * self.__helpers["Qd_lim/u_lim"]

    def __find_output(self) -> float:
        if self.__data["h"][-1] < 0: return 0
        return self.__beta * np.sqrt(self.__data["h"][-1])

    def __quantitize_substance(self) -> float:
        return self.__helpers["Tp/A"] * (self.__data["Qd"][-1] - self.__data["Qo"][-1]) + self.__data["h"][-1]

    def __should_terminate(self) -> bool:
        self.__remaining_cycles -= 1
        return 0 >= self.__remaining_cycles

    # Convert into DataFrame
    def __finalize_data(self):
        self.dataframe = pd.DataFrame.from_dict(self.__data)
        self.dataframe = self.dataframe.groupby(
            self.dataframe['h'].mul(1 / self.__save_tolerance).round()).max().reset_index(drop=True)

        # t, h,u,e,Qd,Qo
        self.dataframe = pd.concat(
            [pd.DataFrame.from_dict({"t": [0], "h": [self.__h_initial], "u": [0], "e": [0], "Qd": [0], "Qo": [0]}),
             self.dataframe])

        self.dataframe = self.dataframe.round(round(np.log10(int(1 / self.__save_tolerance))))
