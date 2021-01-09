from dash_bootstrap_components import Input
from dash_html_components import Output

from imports import *
from processII import ControlSystem
from dash.dependencies import Input, Output, State, MATCH, ALL
import plotly.express as px


class App(object):
    def __init__(self):

        # Color Scheme
        # 'lightBlue''yellow''orange''lightViolet''green''Blue''pink''lightGreen''ugly''violet''gray'
        color_names = ['lightBlue', 'yellow', 'orange', 'lightViolet', 'green',
                       'blue', 'pink', 'lightGreen', 'ugly', 'violet', 'gray']
        self.colors = dict(zip(color_names, px.colors.qualitative.Pastel))

        # Containers for Data Frames and Figures
        self.default_config: Dict[str, Union[int, float]] = {
            "t": 5000,
            "Tp": 0.1,
            "Ti": 0.25,
            "Td": 0.01,

            "g": 10,
            "L": 10,
            "A": 0.01,
            "K": 1,
            "eta_T": 0.9,

            "u_min": 0,
            "u_max": 1_000,

            "P_init": 0,
            "P_dest": 5600_000,
            "ro": 1000,

            "kp": 0.00015,
            "beta": 0.00035,
            # "iteration_limit": 100_000,
            "save_tolerance": 0.001
        }
        #     {
        #     # Kontrola Symulacji
        #     "P_init": 0,  # Poziom Wody
        #     "h_dest": 1.5,  # #### #### ##
        #     "h_min": 0,  # #### #### ####
        #     "h_max": 10,  # #### #### ####
        #     "Qd_min": 0,  # Natężenie dopływu
        #     "Qd_max": 0.05,  # #### #### ####
        #
        #     # Środowisko Symulacji
        #     "u_min": 0,  # Wielkość sterująca
        #     "u_max": 10,  # #### #### #### ##
        #     "A": 2,  # Przekrój poprzeczny
        #     "kp": 0.0015,  # Wzmocnienie Regulatora
        #     "beta": 0.035,  # Współczynnik wypływu
        #     # Czas i Zapis
        #     "t": 5000,  # Czas
        #     "Tp": 0.1,  # ####
        #     "Ti": 0.25,  # ###
        #     "Td": 0.01,  # ###
        #     "save_tolerance": 0.001,  # Tolerancja zapisu
        #
        #     "iteration_limit": 100_000,
        # }

        self.chart_configs: Dict[str, Dict] = dict()
        self.active_config: Dict[str, Union[int, float]] = self.default_config.copy()
        self.current_chart_count = None
        self.selected_chart_index = None

        self.dataframes: Dict[str, pd.DataFrame] = dict()
        self.figures: Dict[str, plt.Figure] = dict()
        self.tabs: List[dcc.Tab] = []
        self.display_tabs: List = []

        # App initialization
        self.app = dash.Dash(name=__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

        # App Configuration
        self.__init_config()
        self.__controller()

    def __controller(self):

        # Update Parameter page content
        self.app.callback(Output('parameter-content', 'children'),
                          Input('parameter-dropdown', 'value'))(self.__controller_parameter_page)

        # Update config Parameter
        self.app.callback(Output('display-config-current', 'children'),
                          Input({"type": "dynamic-parameter", "index": ALL}, 'value'))(self.__controller_parameters)

        # Update Config Displays
        self.app.callback([Output('display-config-group', 'children'),
                           Output('charts-output', 'children')],
                          Input('update-charts-button', 'n_clicks'))(self.__controller_charts_datafigures)

        # Update Sidebar buttons mess MESS
        self.app.callback([Output('display-data', 'children'),
                           Output('tabs-config-picker', 'children'),
                           Output('tabs-config-picker', 'value')],
                          [Input('chart-config-count', 'value'),
                           Input('default-parameters-button', 'n_clicks'),
                           Input('update-config-button', 'n_clicks')],
                          [State('tabs-config-picker', 'value')])(self.__controller_sidebar_buttons)

    def __init_config(self):
        self.app.title = "PA-Symulacja Wody"
        self.app.config.suppress_callback_exceptions = True

        # Styles
        SIDEBAR_STYLE = {'position': 'fixed',
                         'top': 0,
                         'left': 0,
                         'bottom': 0,
                         'width': '26%',
                         'padding': '20px 10px',
                         'backgroundColor': '#eadbff'}
        CONTENT_STYLE = {'marginLeft': '30%',
                         'marginRight': '5%',
                         'top': 0,
                         'padding': '20px 10px'}
        TEXT_STYLE = {'textAlign': 'center', 'color': '#191970'}
        CARD_TEXT_STYLE = {'textAlign': 'center', 'color': '#0074D9'}
        TAB_STYLE = {'padding': '0', 'lineHeight': '1'}

        # Sidebar
        parameter_input = dbc.FormGroup(children=[
            dcc.Dropdown(
                placeholder="Wybierz...",
                id='parameter-dropdown',
                options=[{'label': 'Środowisko', 'value': 'environment'},
                         {'label': 'Kontrola', 'value': 'control'},
                         {'label': 'Czas i Zapis', 'value': 'time_other'}],
                value=None,
                multi=False),
            html.Div(id="parameter-content"),
        ], id="parameter-input")
        chart_input = dbc.FormGroup(children=[
            dbc.Card([dbc.RadioItems(
                id='chart-config-count',
                options=[{'label': 'Jeden', 'value': 1},
                         {'label': 'Dwa', 'value': 2},
                         {'label': 'Trzy', 'value': 3}],
                value=None,
                inline=True,
                style={'margin': 'auto'})]),
            dcc.Tabs(id='tabs-config-picker', style=TAB_STYLE),
            dbc.Card(
                [dbc.ButtonGroup([
                    dbc.Button('Zaktualizuj', 'update-charts-button', color='primary'),
                    dbc.Button('Zapisz', 'update-config-button', color='primary'), ]),
                    dbc.Button("Domyślne", "default-parameters-button")]
            )], id="charts_input")
        sidebar = dbc.Card(children=[
            html.H2('Wykres', style=TEXT_STYLE),
            chart_input,
            html.H2('Parametryzacja', style=TEXT_STYLE),
            parameter_input
        ], id="sidebar", style=SIDEBAR_STYLE)

        # Display
        charts = html.Div(children=[], id="charts-output")

        results = dbc.Row(id="display-data")
        display = html.Div(children=[
            html.H2('Wykresy', style=TEXT_STYLE),
            html.Hr(),
            charts,

            html.Div([html.H2('Dane', style=TEXT_STYLE),
                      html.Hr(),
                      results]),
        ], id="display", style=CONTENT_STYLE)

        # Finalize
        self.app.layout = html.Div(children=[
            html.P(children=None, id='dummy-handler'),
            sidebar,
            display,
        ], id="page")

    def run_server(self, **kwargs):
        self.app.run_server(**kwargs)

    def __controller_parameter_page(self, active_page: str):
        if active_page == "environment":
            return html.Div([
                dbc.Card([
                    html.H6('Poziom początkowy [m]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'P_init'},
                               value=self.default_config['P_init'],
                               min=0,
                               max=self.default_config['P_init'],
                               step=0.01),
                ], id={"type": "araara", "index": "ara"}),
                dbc.Card([
                    html.H6('Poziom oczekiwany  [m]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'P_dest'},
                               value=self.default_config['P_dest'],
                               min=0,
                               max=self.default_config['P_dest'],
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Limit poziomu [m]', style={'textAlign': 'center'}),
                    dcc.RangeSlider(tooltip={'placement': 'bottom'},
                                    id={'type': 'dynamic-parameter', 'index': 'h_lim'},
                                    allowCross=False,
                                    min=self.default_config['h_min'],
                                    max=self.default_config['h_max'],
                                    value=[self.default_config['h_min'], self.default_config['h_max']],
                                    step=0.01),
                ]),
                dbc.Card([
                    html.H6('Limit dopływu [m^3]', style={'textAlign': 'center'}),
                    dcc.RangeSlider(tooltip={'placement': 'bottom'},
                                    id={'type': 'dynamic-parameter', 'index': 'Qd_lim'},
                                    allowCross=False,
                                    min=self.default_config['Qd_min'],
                                    max=self.default_config['Qd_max'],
                                    value=[self.default_config['Qd_min'], self.default_config['Qd_max']],
                                    step=0.01),
                ]),

                #         f"Poziom początkowy: {data['P_initial']} [m]",
                #         f"Poziom oczekiwany: {data['P_dest']} [m]",
                #         f"Limit poziomu: od {data['h_min']} do {data['h_max']} [m]",
                #         f"Limit dopływu: od {data['Qd_min']} do {data['Qd_max']} [m^3]",
            ])
        if active_page == "control":
            return html.Div([
                dbc.Card([
                    html.H6('Limit wielkości sterującej [-]', style={'textAlign': 'center'}),
                    dcc.RangeSlider(tooltip={'placement': 'bottom'},
                                    id={'type': 'dynamic-parameter', 'index': 'u_lim'},
                                    allowCross=False,
                                    min=self.default_config['u_min'],
                                    max=self.default_config['u_max'],
                                    value=[self.default_config['u_min'], self.default_config['u_max']],
                                    step=0.01),
                ]),
                dbc.Card([
                    html.H6('Przekrój poprzeczny zbiornika [m^2]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'A'},
                               value=self.default_config['A'],
                               min=0,
                               max=self.default_config['A'],
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Wzmocnienie Regulatora [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'kp'},
                               value=self.default_config['kp'],
                               min=0,
                               max=self.default_config['kp'],
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Współczynnik wypływu [s^{5/2}/s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'beta'},
                               value=self.default_config['beta'],
                               min=0,
                               max=self.default_config['beta'],
                               step=0.01),
                ]),
                #         f"Limit wielkości sterującej: od {data['u_min']} do {data['u_max']}",
                #         f"Przekrój poprzeczny zbiornika: {data['A']} [m^2]",
                #         f"Wzmocnienie Regulatora: {data['kp']} [-]",
                #         f"Współczynnik wypływu: {data['beta']} [s^{{5/2}}/s]",

            ])
        if active_page == "time_other":
            return html.Div([
                dbc.Card([
                    html.H6('Okres symulacji [s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 't'},
                               value=self.default_config['t'],
                               min=0,
                               max=self.default_config['t'],
                               step=0.01)
                ]),
                dbc.Card([
                    html.H6('Okres Wyprzedzenia [s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'Ti'},
                               value=self.default_config['Ti'],
                               min=0,
                               max=self.default_config['Ti'],
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Okres Zdwojenia [s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': "Td"},
                               value=self.default_config['Td'],
                               min=0,
                               max=self.default_config['Td'],
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Częstotliwość Próbkowania [1/s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'Tp'},
                               value=self.default_config['Tp'],
                               min=0,
                               max=self.default_config['Tp'],
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Tolerancja zapisu [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'save_tolerance'},
                               value=self.default_config['save_tolerance'],
                               min=0,
                               max=self.default_config['save_tolerance'],
                               step=0.01),
                ]),
                #         f"Okres symulacji: {data['t']} [s]",
                #         f"Okres Wyprzedzenia: {data['Ti']} [s]",
                #         f"Okres Zdwojenia: {data['Td']} [s]",
                #         f"Częstotliwość Próbkowania: {data['Tp']} [1/s]",
                #         f"Tolerancja zapisu: {data['save_tolerance']} [-]",
            ])
        return html.Div()

    # 'environment''control''time_other'
    def __controller_chart_config_tabs(self, value: int) -> (List[dcc.Tab], None):
        self.chart_configs.clear()
        self.dataframes.clear()
        self.tabs = [dcc.Tab(label=f"Wykres {i} (Pusty)",
                             value=f"config-{i}",
                             id=f"chart-config-{i}",
                             style={'textAlign': 'center', 'backgroundColor': self.colors['orange']},
                             selected_style={'textAlign': 'center', 'backgroundColor': self.colors['yellow']})
                     for i in range(1, (value or -1) + 1)]
        self.config_cards = [dbc.Card([
            dbc.CardHeader(f"Wykres {i}", className="card-title"),
            dbc.CardBody(children="Zaktualizuj!", className="card-text", id=f"display-config-{i}"), ],
            color="secondary", inverse=True)
            for i in range(1, (self.current_chart_count or 0) + 1)]

        self.display_tabs = [
            dbc.Card([dbc.CardHeader("Konfiguracja", className="card-title"),
                      dbc.CardBody("Sam się zaktualizuj!", className="card-text", id="display-config-current")],
                     style={"width": f"{100 / ((self.current_chart_count or 0) + 1)}%"},
                     color="dark", inverse=True),
            dbc.CardGroup(
                self.config_cards,
                style={"width": f"{(self.current_chart_count or 0) * 100 / ((self.current_chart_count or 0) + 1)}%"},
                id="display-config-group")]
        return self.display_tabs, self.tabs, None

    def __controller_charts_datafigures(self, btn1):
        configs = sorted(self.chart_configs.keys())
        for (i, config) in zip(map(lambda x: int(x.split('-')[1]) - 1, configs), configs):
            self.dataframes[config] = ControlSystem(**self.chart_configs[config]).dataframe
            self.config_cards[i].children[1].children = self.__config_string(self.chart_configs[config])

        x_axis_label = 'Czas regulacji t [s]'
        y_axis_label = 'Natężenie Q(t) [m^3 / s]'
        title = 'Natężenie dopływu i odpływu w czasie'

        if not self.dataframes: return [self.config_cards, None]

        figures = []

        # Poziom Wody
        title = "Woda od czasu"
        fig = go.Figure()
        for (name, df) in self.dataframes.items():
            fig.add_trace(go.Scatter(x=df['t'], y=df['P'], mode='lines+markers', name=f"{name}-Poziom Wody"))
        fig.add_shape(type="line",
                      x0=0,
                      y0=self.active_config['P_dest'],
                      x1=self.active_config['t'],
                      y1=self.active_config['P_dest'])
        figures.append(dcc.Graph(figure=fig))

        # Poziom Wpływ wypływ
        title = "Wpływ wypływ od czasu"
        fig = go.Figure()
        for (name, df) in self.dataframes.items():
            fig.add_trace(go.Scatter(x=df['t'], y=df['Q'], mode='lines+markers', name=f"{name}-Wpływ"))
            fig.add_trace(go.Scatter(x=df['t'], y=df['S'], mode='lines+markers', name=f"{name}-Odpływ"))
        figures.append(dcc.Graph(figure=fig))

        # Poziom Napięcie sterujące
        title = "Napięcie od czasu"
        fig = go.Figure()
        for (name, df) in self.dataframes.items():
            fig.add_trace(go.Scatter(x=df['t'], y=df['u'], mode='lines+markers', name=f"{name}-steer"))
        figures.append(dcc.Graph(figure=fig))

        # Poziom Wody
        title = "Wpływ od sterującej"
        fig = go.Figure()
        for (name, df) in self.dataframes.items():
            fig.add_trace(go.Scatter(x=df['u'], y=df['Q'], mode='lines+markers', name=f"{name}-Wpływ"))
        figures.append(dcc.Graph(figure=fig))
        return [self.config_cards, figures]

    def __controller_sidebar_buttons(self, chart_count, btn1, btn2, selected_chart):
        # 'tabs-config-picker', 'value'
        def set_default_config():
            self.active_config = self.default_config.copy()

        def update_config():
            self.chart_configs[selected_chart] = self.active_config.copy()
            is_default = self.active_config == self.default_config

            self.tabs[self.selected_chart_index - 1] = dcc.Tab(
                label=f"Wykres {self.selected_chart_index}" + (" (auto)" if is_default else ' (custom)'),
                value=f"config-{self.selected_chart_index}",
                id=f"chart-config-{self.selected_chart_index}",
                style={'textAlign': 'center',
                       'backgroundColor': self.colors['lightBlue' if is_default else 'lightGreen']},
                selected_style={'textAlign': 'center',
                                'backgroundColor': self.colors['blue' if is_default else 'green']})

        if chart_count != self.current_chart_count:
            self.current_chart_count = chart_count
            return self.__controller_chart_config_tabs(chart_count)
        if not selected_chart or not self.tabs: return self.display_tabs, self.tabs, None

        self.selected_chart_index = int(selected_chart.split('-')[1])
        if context := dash.callback_context:
            button_id = context.triggered[0]['prop_id'].split('.')[0]
            if button_id == 'default-parameters-button':
                set_default_config()
            elif button_id == 'update-config-button':
                update_config()
        return self.display_tabs, self.tabs, selected_chart

    def __controller_parameters(self, *children):
        slider_data: Dict[str] = dash.callback_context.triggered[0]

        id_: str
        for id_ in re.findall(r'\"index\":\"(.+?)\"', slider_data['prop_id']):
            if 'lim' in id_:
                id_ = id_.split('_')[0]
                self.active_config[f"{id_}_min"] = slider_data['value'][0]
                self.active_config[f"{id_}_max"] = slider_data['value'][1]
            else:
                self.active_config[id_] = slider_data['value']
        return self.__config_string(self.active_config)

    @staticmethod
    def __config_string(data: dict):
        return list(map(lambda x: html.H6(x), [
            f"Środowisko Symulacji",
            f"Poziom początkowy: {data['P_init']} [m]",
            f"Poziom oczekiwany: {data['P_dest']} [m]",
            # f"Limit poziomu: od {data['h_min']} do {data['h_max']} [m]",
            # f"Limit dopływu: od {data['Qd_min']} do {data['Qd_max']} [m^3]",
            f"Kontrola Symulacji",
            # f"Limit wielkości sterującej: od {data['u_min']} do {data['u_max']}",
            # f"Przekrój poprzeczny zbiornika: {data['A']} [m^2]",
            # f"Wzmocnienie Regulatora: {data['kp']} [-]",
            # f"Współczynnik wypływu: {data['beta']} [s^{{5/2}}/s]",
            # f"Czas i Zapis",
            # f"Okres symulacji: {data['t']} [s]",
            # f"Okres Wyprzedzenia: {data['Ti']} [s]",
            # f"Okres Zdwojenia: {data['Td']} [s]",
            # f"Częstotliwość Próbkowania: {data['Tp']} [1/s]",
            # f"Tolerancja zapisu: {data['save_tolerance']} [-]",
        ]))
