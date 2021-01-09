from app import App
# from process import ControlSystem
from processII import ControlSystem, config

if __name__ == '__main__':
    # config = {
    #     "t": 5000,
    #     "Tp": 0.1,
    #     "h_min": 0,
    #     "h_max": 10,
    #     "u_min": 0,
    #     "u_max": 10,
    #     "Qd_min": 0,
    #     "Qd_max": 0.05,
    #     "h_initial": 0,
    #     "h_dest": 1.5,
    #     "kp": 0.0015,
    #     "Ti": 0.25,
    #     "Td": 0.01,
    #     "A": 2,
    #     "beta": 0.035,
    #     "iteration_limit": 100_000,
    #     "save_tolerance": 0.001
    # }

    print(ControlSystem(**config).dataframe)
    # App().run_server(debug=True)
