from imports import *


class ControlSystem(object):
    def __init__(self,
                 g: float,
                 eta_T: float,
                 L: float,

                 A: float,
                 K: float,

                 ro: float,

                 P_init: float,
                 P_dest: float,
                 beta: float,

                 t: float,
                 Tp: float,
                 kp: float,
                 Ti: float,
                 Td: float,
                 save_tolerance: float, **kwargs):
        """Klasa przetrzymujący układ automatycznej regulacji UAR
        W tym przypadku UAR zbudowany ze Tego i tamtego, przy założeniach, że
        Odległość między cząsteczkami wody jest stała
        Ściany kanału jednostki wodnej są stale sztywne
        Efektywność eta_T jest stała,
        wygenerowane dane zwrotne są w "dataframe"

        :param t: Czas symulacji
        :param Tp: Czas próbkowania dla P
        :param Ti: Czas próbkowania dla I
        :param Td: Czas próbkowania dla D
        :param ro: Gęstość Substancji

        :param P_init: Początkowa Moc
        :param P_dest: Cel Energii
        :param kp: wzmocnienie regulatora
        :param beta: śmieszna stała sterująca haha

        :param mu: oporność hydrauliczna turbiny
        :param mu_da: oporność hydrauliczna turbiny powodowana przez operowanie turbiny
        :param mu_cent: oporność hydrauliczna spowodowana siłami dośrodkowymi
        :param g: Stała grawitacji
        :param W_W: Bezwładność Q
        :param T_W: Stała czasu
        :param H: Ciśnienie wody na turbinę
        :param Q: Konsumpcja Wody
        :param H_H: stała ciśnienia mini-HPS
        :param h_loss: utrata ciśnienia
        :param L: Odległość
        :param S: Powierzchnia przekroju
        :param A: Oporność materiału wykonania rury
        :param K_l: Korekta współczynnika A
        :param P_T: Moc mechaniczna
        :param M_T: Moment mechaniczny
        :param M_E: Moment elektromagnetyczny
        :param omega: prędkość kątowa

        :param J * (d*omega)/dt: Ruch podstawy HU
        :param save_tolerance: Tolerancja zapisu odczytu [-]
        """
        self.beta = beta

        self.g = g
        self.eta_T = eta_T
        self.L = L
        self.ro = ro

        self.H_H = g * L * ro

        self.A = A
        self.K = K

        self.P_init = P_init
        self.P_dest = P_dest

        # Dummy Variables
        self.dataframe: pd.DataFrame = pd.DataFrame()

        # Data Initialization
        self.__kp: float = kp

        self.__t: float = t
        self.__Tp: float = Tp
        self.__Ti: float = Ti
        self.__Td: float = Td

        self.__P_min: float = 0
        self.__P_max: float = 1

        self.__u_min: float = 0
        self.__u_max: float = 1

        # Computed Data
        self.__data: Dict[str, List[float]] = {
            "t": [0], "P": [0], "e": [0], "u": [0], "S": [0], "H": [0], "Q": [0], "H_loss": [0], "delta_H": [0],
        }

        self.__helpers: Dict[str, float] = {
            "Tp/Ti": self.__Tp / self.__Ti or 0, "Td/Tp": self.__Td / self.__Ti or 0, "sum_e": 0,
            "Qd_lim/u_lim": 0, "L/g": self.L / self.g,
            "previous_save": 0, "root(2gL)": np.sqrt(2 * self.g * self.L),
            "geta_T": self.g * self.eta_T,
            "AKL": self.A * self.K * self.L,
        }

        # self.__iteration: int = 0
        # self.__iteration_limit: int = iteration_limit
        self.__save_tolerance: float = save_tolerance
        self.__remaining_cycles: int = 100000
        self.__iteration_count: int = 0
        # Calculate Data
        self.__init_control_flow()
        self.__finalize_data()

    def __init_control_flow(self):
        while not self.__should_terminate():
            self.__process_step()

    def __process_step(self):
        self.__data["t"].append(self.__iteration_count)

        self.__data["e"].append(self.__find_control_difference())
        self.__helpers["sum_e"] += self.__data["e"][-1]

        self.__data["u"].append(self.__find_steer())
        self.__data["delta_H"].append(self.__find_pressure_difference())
        self.__data["H"].append(self.__find_pressure())
        self.__data["S"].append(self.__find_cross_section())

        self.__data["H_loss"].append(self.__find_pressure_loss())
        self.__data["Q"].append(self.__find_flow_rate())
        self.__data["P"].append(self.__quantitize_power())

    def __find_control_difference(self) -> float:
        return self.P_dest - self.__data["P"][-1]

    def __find_steer(self) -> float:
        h = self.__data["e"][-1]
        f = self.__helpers["Tp/Ti"] * self.__helpers["sum_e"]
        g = self.__helpers["Td/Tp"] * (self.__data["e"][-1] - self.__data["e"][-2])
        e = self.__kp * (h + f + g)
        k = max(self.__u_min, min(self.__u_max, e))
        return k

    def __find_cross_section(self):
        return self.__data["u"][-1] * self.beta

    def __find_flow_rate(self) -> float:
        return self.__data["S"][-1] * self.__helpers["root(2gL)"]

    def __find_pressure_loss(self):
        return self.__helpers["AKL"] * self.__data["Q"][-1] ** 2

    def __find_pressure_difference(self):
        if self.__data["S"][-1] == 0: return 0
        return -self.__helpers["L/g"] / self.__data["S"][-1] * (self.__data["Q"][-1] - self.__data["Q"][-2])

    def __find_pressure(self):
        return self.H_H + self.__data["delta_H"][-1] - self.__data["H_loss"][-1]

    def __quantitize_power(self) -> float:
        return self.__helpers["geta_T"] * self.__data["Q"][-1] * self.__data["H"][-1]

    def __should_terminate(self) -> bool:
        self.__remaining_cycles -= 1
        self.__iteration_count += 1
        return 0 >= self.__remaining_cycles

    # Convert into DataFrame
    def __finalize_data(self):
        self.dataframe = pd.DataFrame.from_dict(self.__data)
        self.dataframe = self.dataframe.groupby(
            self.dataframe['H'].mul(1 / self.__save_tolerance).round()).max().reset_index(drop=True)
        self.dataframe = pd.concat(
            [pd.DataFrame.from_dict(
                {"t": [0], "H_loss": [0], "e": [self.P_init], "u": [0], "delta_H": [0], "H": [0], "S": [0], "Q": [0]}),
                self.dataframe])

        # self.dataframe.rename(
        #     columns={
        #         "t": "Czas",
        #         "H": "Poziom Wody [m]",
        #         "S": "Wielkość Sterująca [-]",
        #         "e": "Uchyb [m]",
        #         "Q": "Wpływ Wody [m^3/s]",
        #         "P": "Wypływ Wody [m^3/s]"},
        #     inplace=True)
        self.dataframe = self.dataframe.round(round(np.log10(int(1 / self.__save_tolerance))))
