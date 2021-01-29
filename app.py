from dash_bootstrap_components import Input
from dash_html_components import Output

from imports import *
from processII import ControlSystem
from dash.dependencies import Input, Output, State, MATCH, ALL
import plotly.express as px

config = {
    "t": 10,  # okres symulacji [s]                             # Czas od 0 do 100
    "Tp": 0.05,  # czestotlowsc probkowania [1/s]                  # od 0.05 do 1
    "Ti": 0.25,  # okres zdwojenia [s]                             # od 0.05 do 1
    "Td": 0.15,  # okres wyprzedzenia [s]                          # od 0.05 do 1

    "g": 9.81,  # stała grawitacji [m/s^2]                        # od 1 do 25
    "L": 10,  # dlugosc(wysokosc) rury [m]                      # od 1 do 20
    "A": 0.1,  # współczynnik tarcia rury [-]                    # od 0 do 1
    "K": 2000,  # współczynnik korekty tarcia [-]                 # od 0 do 5000
    "eta_T": 0.8,  # sprawnosc turbiny [-]                           # od 0 do 1
    "ro": 789,  # gestosc cieczy [kg/m^3]                         # od 600 do 1400

    "u_min": 0,  # minimalna wartosc wielkosci sterujacej [V]      # od 0 do n
    "u_max": 185,  # maksymalna wartosc wielkosci sterujacej [V]     # od n do 200

    "P_init": 0,  # poczatkowa wartosc generowanej mocy [W]         # 0
    "P_dest": 1_000,  # docelowa wartosc generowanej mocy [W]           # od 0 do 5_000_000

    "kp": 0.00015,  # wzmocnienie regulatora [-]                      # od 0.0001 do 0.005
    "beta": 0.00025,  # wspolczynnik sterowania szerokością rury [-]    # od 0.001 do 0.05

    "save_tolerance": 0.000001  # tolerancja zapisu                     # od 0.0001 do 0.1
}


class App(object):
    def __init__(self):

        # Color Scheme
        # 'lightBlue''yellow''orange''lightViolet''green''Blue''pink''lightGreen''ugly''violet''gray'
        color_names = ['lightBlue', 'yellow', 'orange', 'lightViolet', 'green',
                       'blue', 'pink', 'lightGreen', 'ugly', 'violet', 'gray']
        self.colors = dict(zip(color_names, px.colors.qualitative.Pastel))

        # Containers for Data Frames and Figures
        self.default_config: Dict[str, Union[int, float]] = config

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
        self.app.title = "PA-Symulacja Cieczy"
        self.app.config.suppress_callback_exceptions = True

        # Styles
        SIDEBAR_STYLE = {'position': 'fixed',
                         'top': 0,
                         'left': 0,
                         'bottom': 0,
                         'width': '26%',
                         'padding': '20px 10px',
                         'backgroundColor': '#cdeefd'}
        CONTENT_STYLE = {'marginLeft': '30%',
                         'marginRight': '5%',
                         'top': 0,
                         'padding': '20 px 10px', }
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
                value=1,
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
                    html.H6('Oczekiwany poziom mocy [W]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'P_dest'},
                               value=self.default_config['P_dest'],
                               min=0,
                               max=5_000_000,
                               step=1000),
                ]),
                dbc.Card([
                    html.H6('Stała grawitacyjna [m/s^2]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'g'},
                               value=self.default_config['g'],
                               min=1,
                               max=20,
                               step=0.05),
                ]),
                dbc.Card([
                    html.H6('Długośc rury [m]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'L'},
                               value=self.default_config['L'],
                               min=1,
                               max=20,
                               step=1),
                ]),
                dbc.Card([
                    html.H6('Sprawność Turbiny [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'eta_T'},
                               value=self.default_config['eta_T'],
                               min=0,
                               max=1,
                               step=0.01),
                ]),

                dbc.Card([
                    html.H6('Gestość Cieczy [kg/m^3]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'ro'},
                               value=self.default_config['ro'],
                               min=600,
                               max=1400,
                               step=5),
                ]),

            ])
        if active_page == "control":
            return html.Div([
                dbc.Card([
                    html.H6('Limity wielkości sterujacej [V]', style={'textAlign': 'center'}),
                    dcc.RangeSlider(tooltip={'placement': 'bottom'},
                                    id={'type': 'dynamic-parameter', 'index': 'u_lim'},
                                    allowCross=False,
                                    value=[self.default_config['u_min'], self.default_config['u_max']],
                                    min=0,
                                    max=400,
                                    step=0.01),
                ]),
                dbc.Card([
                    html.H6('Współczynnik tarcia o rurę [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'A'},
                               value=self.default_config['A'],
                               min=0,
                               max=1,
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Korekta współczynnika tarcia [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'K'},
                               value=self.default_config['K'],
                               min=1,
                               max=500,
                               step=1),
                ]),
                dbc.Card([
                    html.H6('Wzmocnienie Regulatora [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'kp'},
                               value=self.default_config['kp'],
                               min=0.00005,
                               max=0.0002,
                               step=0.00005),
                ]),
                dbc.Card([
                    html.H6('Współczynnik szerokości [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'beta'},
                               value=self.default_config['beta'],
                               min=0.00005,
                               max=0.0001,
                               step=0.000005),
                ]),
            ])
        if active_page == "time_other":
            return html.Div([
                dbc.Card([
                    html.H6('Okres symulacji [s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 't'},
                               value=self.default_config['t'],
                               min=0,
                               max=100,
                               step=1)
                ]),
                dbc.Card([
                    html.H6('Częstotliwość Próbkowania [1/s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'Tp'},
                               value=self.default_config['Tp'],
                               min=0.01,
                               max=1,
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Okres Zdwojenia [s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'Ti'},
                               value=self.default_config['Ti'],
                               min=0,
                               max=1,
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Okres Wyprzedzenia [s]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': "Td"},
                               value=self.default_config['Td'],
                               min=0,
                               max=1,
                               step=0.01),
                ]),
                dbc.Card([
                    html.H6('Tolerancja zapisu [-]', style={'textAlign': 'center'}),
                    dcc.Slider(tooltip={'placement': 'bottom'},
                               id={'type': 'dynamic-parameter', 'index': 'save_tolerance'},
                               value=self.default_config['save_tolerance'],
                               min=0.01,
                               max=1,
                               step=0.01),
                ]),
            ])
        return html.Div()

    # 'environment''control''time_other'
    def __controller_chart_config_tabs(self, value: int) -> (List[dcc.Tab], None):
        self.chart_configs.clear()
        self.dataframes.clear()
        self.tabs = [dcc.Tab(label=f"Wykres {i} (Pusty)",
                             value=f"config-{i}",
                             id=f"chart-config-{i}",
                             style={'textAlign': 'center', 'backgroundColor': '#FFCE88'},
                             selected_style={'textAlign': 'center', 'backgroundColor': '#E5A345'})
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

        if not self.dataframes: return [self.config_cards, None]

        figures = []

        # Tutaj tworzycie wyresy jakie chcecie według tych schematow na dole ⬇
        # {"t": [0], "H_loss": [0], "e": [self.P_init], "u": [0], "delta_H": [0], "H": [0], "S": [0], "Q": [0]}
        # Poziom Wody
        fig = go.Figure()
        fig.update_layout(
            title="Moc wytwarzana przez turbinę w funkcji czasu",
            xaxis_title="czas [s]",
            yaxis_title="moc [W]",
            legend_title="legenda",
        )
        df: pd.DataFrame
        for (name, df) in self.dataframes.items():
            name = name.replace("config-", "Konfiguracja ")
            fig.add_trace(go.Scatter(x=df['t'], y=df['P'], mode='lines+markers', name=f"{name} - Osiągnięta moc", ))
        figures.append(dcc.Graph(figure=fig))

        # Poziom Wpływ wypływ
        fig = go.Figure()
        fig.update_layout(
            title="Przeplyw cieczy i pole przekroju wplywu do turbiny w zależności od czasu",
            xaxis_title="czas [s]",
            yaxis_title="PW [l/s], PP [cm^2]",
            legend_title="legenda",
        )
        for (name, df) in self.dataframes.items():
            name = name.replace("config-", "Konfiguracja ")
            fig.add_trace(
                go.Scatter(x=df['t'], y=df['Q'] * 1000, mode='lines+markers', name=f"{name} - Przepływ cieczy (PW)"))
            fig.add_trace(go.Scatter(x=df['t'], y=df['S'] * 10000, mode='lines+markers',
                                     name=f"{name} - Pole przekroju wpływu (PP)"))
        figures.append(dcc.Graph(figure=fig))

        # Poziom Napięcie sterujące
        fig = go.Figure()
        fig.update_layout(
            title="Przebieg zmian napęcia sterującego w funkcji czasu",
            xaxis_title="czas [s]",
            yaxis_title="napiecie sterujące [V]",
            legend_title="legenda",
        )
        for (name, df) in self.dataframes.items():
            name = name.replace("config-", "Konfiguracja ")
            fig.add_trace(go.Scatter(x=df['t'], y=df['u'], mode='lines+markers', name=f"{name} - Osiągnięta wielkość sterująca"))
        figures.append(dcc.Graph(figure=fig))

        # Poziom Wody
        fig = go.Figure()
        fig.update_layout(
            title="Przepływ cieczy w funkcji napięcia sterujacego",
            xaxis_title="napiecie sterujące [V]",
            yaxis_title="przepływ cieczy [l/s]",
            legend_title="legenda",
        )
        for (name, df) in self.dataframes.items():
            name = name.replace("config-", "Konfiguracja ")
            fig.add_trace(go.Scatter(x=df['u'], y=df['Q'] * 1000, mode='lines+markers', name=f"{name} - Osiągnięty przepływ cieczy"))
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
                label=f"Wykres {self.selected_chart_index}" + (" (domyślny)" if is_default else ' (użytkownika)'),
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
        '''
        Funkcja służąca do akutalizacji danych wybranych na suwaku, na podstawie id suwaka.
        Na bieząco aktualizuje też kartę z wypisywaną konfiguracją.
        '''
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
            f"────────────────────",
            f"Poziom początkowy",
            f"{data['P_init']} [W]",
            f"Poziom oczekiwany",
            f"{data['P_dest']} [W]",
            f"Sprawność Turbiny",
            f"{data['eta_T']} [-]",
            f"Długośc rury",
            f"{data['L']} [m]",
            f"Gęstość cieczy",
            f"{data['ro']} [kg/m^3]",
            f"Stała Grawitacji",
            f"{data['g']} [m/s^2]",
            f"Współczynnik Tarcia rury",
            f"{data['A']} [-]",
            f"Korekta tarcia",
            f"{data['K']} [-]",
            f"────────────────────",
            f"Kontrola Symulacji",
            f"────────────────────",
            f"Limit wielkości sterującej",
            f"{data['u_min']} do {data['u_max']}",
            f"Wzmocnienie Regulatora",
            f"{data['kp']} [-]",
            f"Współczynnik szerokości",
            f"{data['beta']} [-]",
            f"────────────────────",
            f"Czas i Zapis",
            f"────────────────────",
            f"Okres symulacji",
            f"{data['t']} [s]",
            f"Częstotliwość Próbkowania",
            f"{data['Tp']} [1/s]",
            f"Okres Zdwojenia",
            f"{data['Ti']} [s]",
            f"Okres Wyprzedzenia",
            f"{data['Td']} [s]",
            f"Tolerancja zapisu",
            f"{data['save_tolerance']} [-]",
        ]))
