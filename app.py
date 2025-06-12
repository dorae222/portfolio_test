#!/usr/bin/env python
# -*- coding: utf-8 -*-

import dash
from dash import dcc, html, Input, Output, State, callback_context, ALL
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime
import json

# Dash 앱 초기화
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

# 색상 팔레트 정의
COLORS = {
    'principal': '#3498db',
    'interest': '#2ecc71',
    'stocks_kr': '#e74c3c',
    'stocks_global': '#f39c12',
    'reits': '#9b59b6',
    'bonds': '#1abc9c',
    'deposits': '#34495e',
    'crypto': '#e67e22'
}

# 한국인 평균 투자 데이터 (조사 자료 기반)
KOREAN_AVG_DATA = {
    'monthly_income': 4050000,  # 월평균 가구소득
    'savings_rate': 0.281,  # 저축률 28.1%
    'monthly_investment': 1138050,  # 월평균 투자가능금액
    'asset_allocation': {
        'real_estate': 0.80,
        'financial_assets': 0.16,
        'others': 0.04
    }
}

# 리스크 프로필별 자산 배분
RISK_PROFILES = {
    'conservative': {
        'stocks_kr': 0.20,
        'stocks_global': 0.05,
        'reits': 0.10,
        'bonds': 0.50,
        'deposits': 0.15,
        'crypto': 0.00
    },
    'moderate': {
        'stocks_kr': 0.35,
        'stocks_global': 0.15,
        'reits': 0.15,
        'bonds': 0.25,
        'deposits': 0.10,
        'crypto': 0.00
    },
    'aggressive': {
        'stocks_kr': 0.40,
        'stocks_global': 0.25,
        'reits': 0.10,
        'bonds': 0.15,
        'deposits': 0.05,
        'crypto': 0.05
    }
}

# 자산별 기본 수익률 (조사 자료 기반)
DEFAULT_RETURNS = {
    'single_asset': 0.06,
    'stocks_kr': 0.08,
    'stocks_global': 0.10,
    'reits': 0.05,
    'bonds': 0.035,
    'deposits': 0.03,
    'crypto': 0.15
}

# 자산별 변동성 (표준편차)
ASSET_VOLATILITY = {
    'stocks_kr': 0.20,
    'stocks_global': 0.18,
    'reits': 0.15,
    'bonds': 0.05,
    'deposits': 0.01,
    'crypto': 0.70
}

# 자산 이름 매핑
ASSET_NAMES = {
    'stocks_kr': 'Korean Stocks',
    'stocks_global': 'Global Stocks',
    'reits': 'REITs',
    'bonds': 'Bonds',
    'deposits': 'Deposits/MMF',
    'crypto': 'Cryptocurrency'
}

def calculate_future_value(principal, monthly_payment, annual_rate, years, compound_frequency='monthly'):
    """복리 계산 함수"""
    if compound_frequency == 'monthly':
        r = annual_rate / 12
        n = years * 12
    else:  # yearly
        r = annual_rate
        n = years
    
    # 초기 투자금의 미래가치
    fv_principal = principal * (1 + r) ** n
    
    # 월 납입금의 미래가치 (적금 공식)
    if r > 0:
        fv_payments = monthly_payment * (((1 + r) ** n - 1) / r)
    else:
        fv_payments = monthly_payment * n
    
    return fv_principal + fv_payments

def generate_year_by_year_data(principal, monthly_payment, annual_rate, years):
    """연도별 상세 데이터 생성"""
    data = []
    current_balance = principal
    total_invested = principal
    
    for year in range(1, years + 1):
        # 연간 수익 계산
        yearly_return = current_balance * annual_rate
        yearly_investment = monthly_payment * 12
        
        # 월별 복리 계산
        for month in range(12):
            current_balance = current_balance * (1 + annual_rate/12) + monthly_payment
        
        total_invested += yearly_investment
        
        data.append({
            'Year': year,
            'Beginning Balance': current_balance - yearly_return - yearly_investment,
            'Annual Investment': yearly_investment,
            'Interest Earned': yearly_return,
            'Ending Balance': current_balance,
            'Total Invested': total_invested,
            'Total Interest': current_balance - total_invested
        })
    
    return pd.DataFrame(data)

def calculate_portfolio_returns(allocations, returns, principal, monthly_payment, years):
    """포트폴리오 수익률 계산"""
    portfolio_data = []
    
    for asset, allocation in allocations.items():
        if allocation > 0:
            asset_principal = principal * allocation
            asset_monthly = monthly_payment * allocation
            asset_return = returns[asset]
            
            # 자산별 미래가치 계산
            fv = calculate_future_value(asset_principal, asset_monthly, asset_return, years)
            
            # 연도별 데이터 생성
            yearly_data = generate_year_by_year_data(asset_principal, asset_monthly, asset_return, years)
            yearly_data['Asset'] = asset
            yearly_data['Allocation'] = allocation
            
            portfolio_data.append(yearly_data)
    
    return pd.concat(portfolio_data, ignore_index=True) if portfolio_data else pd.DataFrame()

# 레이아웃 정의
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("Investment Performance Simulator", className="text-center mb-4"),
            html.P("장기 투자 성과를 시뮬레이션하고 최적의 투자 전략을 찾아보세요", className="text-center text-muted mb-4")
        ])
    ]),
    
    dcc.Tabs(id="main-tabs", value="simple", children=[
        dcc.Tab(label="Stage 1: Simple Investment", value="simple", children=[
            dbc.Row([
                # 왼쪽 패널 - 입력 컨트롤
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Investment Parameters", className="mb-4"),
                            
                            # 초기 투자금
                            html.Label("Initial Investment (만원)", className="mt-3"),
                            dcc.Slider(
                                id="initial-investment",
                                min=100,
                                max=10000,
                                step=10,
                                value=1000,
                                marks={i: f'{i:,}' for i in [100, 2500, 5000, 7500, 10000]},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            
                            # 월 투자금
                            html.Label("Monthly Investment (만원)", className="mt-4"),
                            dcc.Slider(
                                id="monthly-investment",
                                min=10,
                                max=500,
                                step=5,
                                value=114,
                                marks={i: f'{i}' for i in [10, 100, 200, 300, 400, 500]},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            
                            # 연간 수익률
                            html.Label("Expected Annual Return (%)", className="mt-4"),
                            dcc.Slider(
                                id="annual-return",
                                min=-10,
                                max=30,
                                step=0.5,
                                value=6,
                                marks={i: f'{i}%' for i in [-10, -5, 0, 5, 10, 15, 20, 25, 30]},
                                tooltip={"placement": "bottom", "always_visible": True}
                            ),
                            
                            # 프리셋 버튼
                            html.Div([
                                dbc.ButtonGroup([
                                    dbc.Button("Deposit(3%)", id="preset-deposit", size="sm", outline=True),
                                    dbc.Button("Bond(3.5%)", id="preset-bond", size="sm", outline=True),
                                    dbc.Button("Stock(8%)", id="preset-stock", size="sm", outline=True),
                                    dbc.Button("Aggressive(12%)", id="preset-aggressive", size="sm", outline=True),
                                ], className="mt-2")
                            ]),
                            
                            # 투자 기간
                            html.Label("Investment Period", className="mt-4"),
                            dcc.Dropdown(
                                id="investment-years",
                                options=[
                                    {'label': '5 Years', 'value': 5},
                                    {'label': '10 Years', 'value': 10},
                                    {'label': '15 Years', 'value': 15},
                                    {'label': '20 Years', 'value': 20},
                                    {'label': '30 Years', 'value': 30},
                                ],
                                value=20
                            ),
                            
                            # 옵션 토글
                            html.Hr(className="mt-4"),
                            dbc.Checklist(
                                id="chart-options",
                                options=[
                                    {"label": "Apply Inflation (2.5%)", "value": "inflation"},
                                    {"label": "Apply Tax", "value": "tax"},
                                ],
                                value=[],
                                switch=True,
                            ),
                            
                            # 복리 주기
                            html.Label("Compound Frequency", className="mt-3"),
                            dbc.RadioItems(
                                id="compound-frequency",
                                options=[
                                    {"label": "Monthly", "value": "monthly"},
                                    {"label": "Yearly", "value": "yearly"},
                                ],
                                value="monthly",
                                inline=True
                            ),
                        ])
                    ])
                ], width=3),
                
                # 중앙 - 차트
                dbc.Col([
                    dcc.Graph(id="simple-investment-chart"),
                    
                    # 연도별 상세 테이블
                    html.Div(id="yearly-details-table", className="mt-4")
                ], width=6),
                
                # 오른쪽 패널 - 결과 요약
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Investment Summary", className="mb-4"),
                            html.Div(id="investment-summary"),
                            
                            html.Hr(className="my-4"),
                            
                            html.H5("Investment Insights", className="mb-3"),
                            html.Div(id="investment-insights")
                        ])
                    ])
                ], width=3),
            ])
        ]),
        
        dcc.Tab(label="Stage 2: Portfolio Investment", value="portfolio", children=[
            dbc.Row([
                # 왼쪽 패널 - 포트폴리오 설정
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Portfolio Settings", className="mb-4"),
                            
                            # 리스크 성향
                            html.Label("Risk Profile", className="mt-3"),
                            dbc.RadioItems(
                                id="risk-profile",
                                options=[
                                    {"label": "Conservative", "value": "conservative"},
                                    {"label": "Moderate", "value": "moderate"},
                                    {"label": "Aggressive", "value": "aggressive"},
                                    {"label": "Custom", "value": "custom"},
                                ],
                                value="moderate",
                                inline=False
                            ),
                            
                            # 초기 투자금 & 월 투자금 (포트폴리오용)
                            html.Label("Initial Investment (만원)", className="mt-4"),
                            dcc.Input(
                                id="portfolio-initial",
                                type="number",
                                value=1000,
                                min=100,
                                max=100000,
                                step=100,
                                className="form-control"
                            ),
                            
                            html.Label("Monthly Investment (만원)", className="mt-3"),
                            dcc.Input(
                                id="portfolio-monthly",
                                type="number",
                                value=114,
                                min=10,
                                max=1000,
                                step=10,
                                className="form-control"
                            ),
                            
                            html.Label("Investment Period (Years)", className="mt-3"),
                            dcc.Input(
                                id="portfolio-years",
                                type="number",
                                value=20,
                                min=1,
                                max=50,
                                step=1,
                                className="form-control"
                            ),
                            
                            # 리밸런싱 옵션
                            html.Hr(className="my-4"),
                            html.Label("Rebalancing", className="mt-3"),
                            dcc.Dropdown(
                                id="rebalancing-period",
                                options=[
                                    {'label': 'None', 'value': 'none'},
                                    {'label': 'Yearly', 'value': 'yearly'},
                                    {'label': 'Semi-annually', 'value': 'semi'},
                                    {'label': 'Quarterly', 'value': 'quarterly'},
                                ],
                                value='yearly'
                            ),
                            
                            # 라이프사이클 투자
                            dbc.Checklist(
                                id="lifecycle-investing",
                                options=[
                                    {"label": "Apply Lifecycle Investing", "value": "lifecycle"},
                                ],
                                value=[],
                                switch=True,
                                className="mt-3"
                            ),
                        ])
                    ])
                ], width=3),
                
                # 중앙 상단 - 자산 배분
                dbc.Col([
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H5("Asset Allocation", className="mb-3"),
                                    # 자산 배분 슬라이더들 - 항상 존재
                                    html.Div([
                                        html.Div([
                                            html.Label("Korean Stocks: 35%", id="label-stocks_kr"),
                                            dcc.Slider(
                                                id="slider-stocks_kr",
                                                min=0, max=100, step=5, value=35,
                                                marks={i: f'{i}%' for i in [0, 25, 50, 75, 100]},
                                                disabled=True
                                            )
                                        ], className="mb-3"),
                                        html.Div([
                                            html.Label("Global Stocks: 15%", id="label-stocks_global"),
                                            dcc.Slider(
                                                id="slider-stocks_global",
                                                min=0, max=100, step=5, value=15,
                                                marks={i: f'{i}%' for i in [0, 25, 50, 75, 100]},
                                                disabled=True
                                            )
                                        ], className="mb-3"),
                                        html.Div([
                                            html.Label("REITs: 15%", id="label-reits"),
                                            dcc.Slider(
                                                id="slider-reits",
                                                min=0, max=100, step=5, value=15,
                                                marks={i: f'{i}%' for i in [0, 25, 50, 75, 100]},
                                                disabled=True
                                            )
                                        ], className="mb-3"),
                                        html.Div([
                                            html.Label("Bonds: 25%", id="label-bonds"),
                                            dcc.Slider(
                                                id="slider-bonds",
                                                min=0, max=100, step=5, value=25,
                                                marks={i: f'{i}%' for i in [0, 25, 50, 75, 100]},
                                                disabled=True
                                            )
                                        ], className="mb-3"),
                                        html.Div([
                                            html.Label("Deposits/MMF: 10%", id="label-deposits"),
                                            dcc.Slider(
                                                id="slider-deposits",
                                                min=0, max=100, step=5, value=10,
                                                marks={i: f'{i}%' for i in [0, 25, 50, 75, 100]},
                                                disabled=True
                                            )
                                        ], className="mb-3"),
                                        html.Div([
                                            html.Label("Cryptocurrency: 0%", id="label-crypto"),
                                            dcc.Slider(
                                                id="slider-crypto",
                                                min=0, max=100, step=5, value=0,
                                                marks={i: f'{i}%' for i in [0, 25, 50, 75, 100]},
                                                disabled=True
                                            )
                                        ], className="mb-3"),
                                    ]),
                                    html.Div(id="allocation-warning", className="text-warning mt-2"),
                                    dcc.Graph(id="allocation-chart", className="mt-3")
                                ])
                            ])
                        ], width=12),
                    ]),
                    
                    # 메인 차트
                    dbc.Row([
                        dbc.Col([
                            dcc.Graph(id="portfolio-performance-chart")
                        ], width=12)
                    ], className="mt-3"),
                ], width=6),
                
                # 오른쪽 패널 - 결과 및 분석
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H4("Portfolio Analysis", className="mb-4"),
                            
                            dcc.Tabs(id="analysis-tabs", value="summary", children=[
                                dcc.Tab(label="Summary", value="summary", children=[
                                    html.Div(id="portfolio-summary", className="mt-3")
                                ]),
                                dcc.Tab(label="Risk Metrics", value="risk", children=[
                                    html.Div(id="risk-metrics", className="mt-3")
                                ]),
                                dcc.Tab(label="Scenarios", value="scenarios", children=[
                                    html.Div([
                                        html.H6("Market Scenarios", className="mt-3"),
                                        dbc.ButtonGroup([
                                            dbc.Button("Bull Market", id="scenario-bull", size="sm"),
                                            dbc.Button("Normal", id="scenario-normal", size="sm"),
                                            dbc.Button("Bear Market", id="scenario-bear", size="sm"),
                                        ]),
                                        html.Div(id="scenario-results", className="mt-3")
                                    ])
                                ])
                            ])
                        ])
                    ])
                ], width=3),
            ])
        ])
    ]),
    
    # 숨겨진 div for storing data
    dcc.Store(id="portfolio-allocations-store"),
], fluid=True)

# 콜백: Simple Investment 계산
@app.callback(
    [Output("simple-investment-chart", "figure"),
     Output("investment-summary", "children"),
     Output("investment-insights", "children"),
     Output("yearly-details-table", "children")],
    [Input("initial-investment", "value"),
     Input("monthly-investment", "value"),
     Input("annual-return", "value"),
     Input("investment-years", "value"),
     Input("chart-options", "value"),
     Input("compound-frequency", "value")]
)
def update_simple_investment(initial, monthly, annual_return, years, options, compound_freq):
    # 금액 단위 변환 (만원 -> 원)
    initial_amount = initial * 10000
    monthly_amount = monthly * 10000
    rate = annual_return / 100
    
    # 인플레이션 적용
    if "inflation" in options:
        rate = rate - 0.025  # 2.5% 인플레이션
    
    # 연도별 데이터 생성
    df = generate_year_by_year_data(initial_amount, monthly_amount, rate, years)
    
    # 세금 적용
    if "tax" in options:
        # 금융소득 종합과세 간단 계산 (이자소득 2000만원 초과시 15.4%)
        df['Tax'] = df['Total Interest'].apply(lambda x: max(0, (x - 20000000) * 0.154) if x > 20000000 else 0)
        df['After Tax Balance'] = df['Ending Balance'] - df['Tax']
        final_value = df.iloc[-1]['After Tax Balance']
    else:
        final_value = df.iloc[-1]['Ending Balance']
    
    # 차트 생성
    fig = go.Figure()
    
    # Stacked bar chart
    fig.add_trace(go.Bar(
        x=df['Year'],
        y=df['Total Invested'],
        name='Principal',
        marker_color=COLORS['principal'],
        hovertemplate='Year: %{x}<br>Principal: ₩%{y:,.0f}<extra></extra>'
    ))
    
    fig.add_trace(go.Bar(
        x=df['Year'],
        y=df['Total Interest'],
        name='Interest',
        marker_color=COLORS['interest'],
        hovertemplate='Year: %{x}<br>Interest: ₩%{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Investment Growth Over Time",
        xaxis_title="Year",
        yaxis_title="Total Value (₩)",
        barmode='stack',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    # 요약 정보
    total_invested = df.iloc[-1]['Total Invested']
    total_interest = df.iloc[-1]['Total Interest']
    roi = (final_value / total_invested - 1) * 100
    
    summary = dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Final Value", className="text-muted"),
                        html.H4(f"₩{final_value:,.0f}", className="text-primary")
                    ])
                ], className="mb-3")
            ])
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Invested", className="text-muted"),
                        html.P(f"₩{total_invested:,.0f}")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Interest", className="text-muted"),
                        html.P(f"₩{total_interest:,.0f}")
                    ])
                ])
            ], width=6)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("ROI", className="text-muted"),
                        html.P(f"{roi:.1f}%")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Multiple", className="text-muted"),
                        html.P(f"{final_value/total_invested:.2f}x")
                    ])
                ])
            ], width=6)
        ])
    ])
    
    # 인사이트 및 투자 조언
    monthly_avg_kr = KOREAN_AVG_DATA['monthly_investment'] / 10000
    compound_ratio = total_interest/final_value*100
    
    # 결과 해석
    interpretation = []
    if compound_ratio > 50:
        interpretation.append("Excellent! Compound interest contributes over 50% of your final wealth.")
    elif compound_ratio > 30:
        interpretation.append("Good progress! Compound interest is working effectively for you.")
    else:
        interpretation.append("Consider longer investment period to maximize compound effect.")
    
    # 투자 전략 제안
    strategies = []
    if annual_return < 5:
        strategies.append("Consider diversifying into higher-yield assets like stocks or REITs")
    elif annual_return > 15:
        strategies.append("High returns come with high risk. Consider balancing with stable assets")
    
    if monthly/monthly_avg_kr < 0.5:
        strategies.append("Try to increase monthly investment to at least 50% of Korean average")
    elif monthly/monthly_avg_kr > 2:
        strategies.append("Great savings rate! Consider tax-advantaged accounts like IRP/ISA")
    
    if years < 10:
        strategies.append("Consider extending investment period to 15+ years for better compound effect")
    
    insights = html.Div([
        html.H6("📊 Result Analysis", className="mb-3 text-primary"),
        html.P(interpretation[0], className="mb-3"),
        
        html.H6("📈 Key Metrics", className="mb-2"),
        html.Ul([
            html.Li(f"Your monthly investment is {monthly/monthly_avg_kr:.1f}x the Korean average"),
            html.Li(f"To reach ₩500M retirement fund: {max(0, 500000000/final_value*years - years):.1f} more years needed"),
            html.Li(f"Compound interest accounts for {compound_ratio:.1f}% of final value"),
            html.Li(f"Your money grows {final_value/total_invested:.2f}x over {years} years")
        ]),
        
        html.H6("💡 Investment Strategy Recommendations", className="mb-2 mt-3"),
        html.Ul([html.Li(strategy) for strategy in strategies]) if strategies else html.P("You're on track! Keep maintaining your current strategy."),
        
        html.Hr(),
        html.H6("🎯 Action Items", className="mb-2"),
        html.Ol([
            html.Li("Review and optimize your asset allocation quarterly"),
            html.Li("Consider increasing monthly investment by 5-10% annually"),
            html.Li("Explore tax-efficient investment vehicles (연금저축, ISA)"),
            html.Li("Build emergency fund of 6-12 months expenses separately")
        ])
    ])
    
    # 연도별 상세 테이블 (최근 5년만 표시)
    table_df = df.tail(5).round(0)
    table = dbc.Table.from_dataframe(
        table_df[['Year', 'Total Invested', 'Total Interest', 'Ending Balance']],
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        size='sm'
    )
    
    return fig, summary, insights, table

# 콜백: 수익률 프리셋 버튼
@app.callback(
    Output("annual-return", "value"),
    [Input("preset-deposit", "n_clicks"),
     Input("preset-bond", "n_clicks"),
     Input("preset-stock", "n_clicks"),
     Input("preset-aggressive", "n_clicks")]
)
def update_return_preset(n1, n2, n3, n4):
    ctx = callback_context
    if not ctx.triggered:
        return 6
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "preset-deposit":
        return 3
    elif button_id == "preset-bond":
        return 3.5
    elif button_id == "preset-stock":
        return 8
    elif button_id == "preset-aggressive":
        return 12
    
    return 6

# 콜백: 리스크 프로필에 따른 슬라이더 업데이트
@app.callback(
    [Output("slider-stocks_kr", "value"),
     Output("slider-stocks_kr", "disabled"),
     Output("slider-stocks_global", "value"),
     Output("slider-stocks_global", "disabled"),
     Output("slider-reits", "value"),
     Output("slider-reits", "disabled"),
     Output("slider-bonds", "value"),
     Output("slider-bonds", "disabled"),
     Output("slider-deposits", "value"),
     Output("slider-deposits", "disabled"),
     Output("slider-crypto", "value"),
     Output("slider-crypto", "disabled")],
    [Input("risk-profile", "value")]
)
def update_sliders_by_profile(risk_profile):
    if risk_profile == "custom":
        # Custom 모드 - 슬라이더 활성화
        return (35, False, 15, False, 15, False, 25, False, 10, False, 0, False)
    else:
        # 프리셋 모드 - 슬라이더 비활성화 및 값 설정
        profile = RISK_PROFILES[risk_profile]
        return (
            int(profile['stocks_kr'] * 100), True,
            int(profile['stocks_global'] * 100), True,
            int(profile['reits'] * 100), True,
            int(profile['bonds'] * 100), True,
            int(profile['deposits'] * 100), True,
            int(profile['crypto'] * 100), True
        )

# 콜백: 슬라이더 값에 따른 레이블 및 데이터 업데이트
@app.callback(
    [Output("label-stocks_kr", "children"),
     Output("label-stocks_global", "children"),
     Output("label-reits", "children"),
     Output("label-bonds", "children"),
     Output("label-deposits", "children"),
     Output("label-crypto", "children"),
     Output("allocation-warning", "children"),
     Output("portfolio-allocations-store", "data")],
    [Input("slider-stocks_kr", "value"),
     Input("slider-stocks_global", "value"),
     Input("slider-reits", "value"),
     Input("slider-bonds", "value"),
     Input("slider-deposits", "value"),
     Input("slider-crypto", "value")]
)
def update_allocation_labels(stocks_kr, stocks_global, reits, bonds, deposits, crypto):
    # 레이블 업데이트
    labels = [
        f"Korean Stocks: {stocks_kr}%",
        f"Global Stocks: {stocks_global}%",
        f"REITs: {reits}%",
        f"Bonds: {bonds}%",
        f"Deposits/MMF: {deposits}%",
        f"Cryptocurrency: {crypto}%"
    ]
    
    # 총합 계산
    total = stocks_kr + stocks_global + reits + bonds + deposits + crypto
    
    # 경고 메시지
    if total != 100:
        warning = f"⚠️ Total allocation: {total}% (should be 100%)"
    else:
        warning = "✅ Total allocation: 100%"
    
    # 자산 배분 데이터
    allocations = {
        'stocks_kr': stocks_kr / 100,
        'stocks_global': stocks_global / 100,
        'reits': reits / 100,
        'bonds': bonds / 100,
        'deposits': deposits / 100,
        'crypto': crypto / 100
    }
    
    return (*labels, warning, allocations)

# 콜백: 자산 배분 차트
@app.callback(
    Output("allocation-chart", "figure"),
    [Input("portfolio-allocations-store", "data")]
)
def update_allocation_chart(allocations):
    if not allocations:
        return go.Figure()
    
    # 0이 아닌 자산만 필터링
    filtered_allocations = {k: v for k, v in allocations.items() if v > 0}
    
    if not filtered_allocations:
        return go.Figure()
    
    labels = [ASSET_NAMES[k] for k in filtered_allocations.keys()]
    values = [v * 100 for v in filtered_allocations.values()]
    colors = [COLORS[asset] for asset in filtered_allocations.keys()]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.3,
        marker_colors=colors,
        textinfo='label+percent',
        textposition='auto'
    )])
    
    fig.update_layout(
        showlegend=True,
        height=300,
        margin=dict(t=20, b=20, l=20, r=20)
    )
    
    return fig

# 콜백: 포트폴리오 성과 계산
@app.callback(
    [Output("portfolio-performance-chart", "figure"),
     Output("portfolio-summary", "children"),
     Output("risk-metrics", "children")],
    [Input("portfolio-allocations-store", "data"),
     Input("portfolio-initial", "value"),
     Input("portfolio-monthly", "value"),
     Input("portfolio-years", "value"),
     Input("rebalancing-period", "value"),
     Input("lifecycle-investing", "value")]
)
def update_portfolio_performance(allocations, initial, monthly, years, rebalancing, lifecycle):
    if not allocations:
        return go.Figure(), "No data", "No data"
    
    returns = DEFAULT_RETURNS
    
    # 금액 단위 변환
    initial_amount = initial * 10000
    monthly_amount = monthly * 10000
    
    # 포트폴리오 데이터 계산
    portfolio_df = calculate_portfolio_returns(allocations, returns, initial_amount, monthly_amount, years)
    
    if portfolio_df.empty:
        return go.Figure(), "No data", "No data"
    
    # 연도별 자산별 합계 계산
    yearly_summary = portfolio_df.groupby(['Year', 'Asset']).agg({
        'Ending Balance': 'sum',
        'Total Invested': 'sum',
        'Total Interest': 'sum'
    }).reset_index()
    
    # Stacked Bar Chart 생성
    fig = go.Figure()
    
    for asset in yearly_summary['Asset'].unique():
        asset_data = yearly_summary[yearly_summary['Asset'] == asset]
        
        # 원금
        fig.add_trace(go.Bar(
            x=asset_data['Year'],
            y=asset_data['Total Invested'],
            name=f'{ASSET_NAMES[asset]} Principal',
            marker_color=COLORS[asset],
            marker_opacity=0.7,
            legendgroup=asset,
            showlegend=True
        ))
        
        # 수익
        fig.add_trace(go.Bar(
            x=asset_data['Year'],
            y=asset_data['Total Interest'],
            name=f'{ASSET_NAMES[asset]} Interest',
            marker_color=COLORS[asset],
            marker_opacity=1.0,
            legendgroup=asset,
            showlegend=True
        ))
    
    fig.update_layout(
        title="Portfolio Performance by Asset",
        xaxis_title="Year",
        yaxis_title="Value (₩)",
        barmode='stack',
        hovermode='x unified',
        template='plotly_white',
        height=500
    )
    
    # 포트폴리오 요약
    final_year_data = portfolio_df[portfolio_df['Year'] == years]
    total_value = final_year_data['Ending Balance'].sum()
    total_invested = final_year_data['Total Invested'].sum()
    total_returns = final_year_data['Total Interest'].sum()
    
    # 가중평균 수익률 계산
    weighted_return = sum(allocations[asset] * returns[asset] for asset in allocations)
    
    # 포트폴리오 전략 제안
    portfolio_advice = []
    
    # 변동성 계산
    portfolio_volatility = np.sqrt(sum(
        (allocations[asset] ** 2) * (ASSET_VOLATILITY.get(asset, 0) ** 2)
        for asset in allocations if asset in ASSET_VOLATILITY
    ))
    
    sharpe_ratio = (weighted_return - 0.03) / portfolio_volatility if portfolio_volatility > 0 else 0
    
    # 변동성 기반 조언
    if portfolio_volatility > 0.20:
        portfolio_advice.append("High volatility detected. Consider reducing crypto/stock allocation")
    elif portfolio_volatility < 0.10:
        portfolio_advice.append("Low volatility portfolio. You could take more risk for higher returns")
    
    # Sharpe ratio 기반 조언
    if sharpe_ratio < 0.5:
        portfolio_advice.append("Poor risk-adjusted returns. Rebalance to more efficient assets")
    elif sharpe_ratio > 1.0:
        portfolio_advice.append("Excellent risk-adjusted returns! Maintain current allocation")
    
    # 자산 배분 조언
    total_equity = allocations.get('stocks_kr', 0) + allocations.get('stocks_global', 0)
    if total_equity > 0.7:
        portfolio_advice.append("Very aggressive allocation. Add bonds/deposits for stability")
    elif total_equity < 0.3:
        portfolio_advice.append("Conservative allocation. Consider more equity exposure for growth")
    
    summary = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H5("Portfolio Value", className="text-primary"),
                html.H3(f"₩{total_value:,.0f}")
            ])
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                html.P(f"Total Invested: ₩{total_invested:,.0f}"),
                html.P(f"Total Returns: ₩{total_returns:,.0f}"),
                html.P(f"Portfolio ROI: {(total_value/total_invested-1)*100:.1f}%"),
                html.P(f"Expected Annual Return: {weighted_return*100:.2f}%")
            ])
        ]),
        html.Hr(),
        html.H6("📋 Portfolio Strategy", className="mb-2"),
        html.Ul([html.Li(advice) for advice in portfolio_advice]) if portfolio_advice else html.P("Well-balanced portfolio!"),
        html.Hr(),
        html.H6("🎯 Optimization Tips", className="mb-2"),
        html.Ol([
            html.Li("Rebalance portfolio annually to maintain target allocation"),
            html.Li("Consider international diversification (30-40% foreign assets)"),
            html.Li("Add alternative assets (REITs, commodities) for better diversification"),
            html.Li("Adjust allocation based on your age (100 - age = equity %)")
        ])
    ])
    
    # 리스크 메트릭스
    max_drawdown = portfolio_volatility * 2  # 간단한 추정
    
    risk_metrics = dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Portfolio Volatility"),
                        html.P(f"{portfolio_volatility*100:.1f}%")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Sharpe Ratio"),
                        html.P(f"{sharpe_ratio:.2f}")
                    ])
                ])
            ], width=6)
        ], className="mb-3"),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Est. Max Drawdown"),
                        html.P(f"-{max_drawdown*100:.1f}%")
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Risk Level"),
                        html.P("Moderate" if portfolio_volatility < 0.15 else "High")
                    ])
                ])
            ], width=6)
        ])
    ])
    
    return fig, summary, risk_metrics

# 콜백: 시나리오 분석
@app.callback(
    Output("scenario-results", "children"),
    [Input("scenario-bull", "n_clicks"),
     Input("scenario-bear", "n_clicks"),
     Input("scenario-normal", "n_clicks")],
    [State("portfolio-allocations-store", "data"),
     State("portfolio-initial", "value"),
     State("portfolio-monthly", "value"),
     State("portfolio-years", "value")]
)
def update_scenario_analysis(bull_clicks, bear_clicks, normal_clicks, allocations, initial, monthly, years):
    ctx = callback_context
    if not ctx.triggered or not allocations:
        return html.P("Click a scenario button to see projections")
    
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # 시나리오별 수익률 조정
    scenario_adjustments = {
        "scenario-bull": {"name": "Bull Market", "multiplier": 1.5, "volatility": 1.2},
        "scenario-bear": {"name": "Bear Market", "multiplier": 0.3, "volatility": 1.8},
        "scenario-normal": {"name": "Normal Market", "multiplier": 1.0, "volatility": 1.0}
    }
    
    if button_id not in scenario_adjustments:
        return html.P("Select a scenario")
    
    scenario = scenario_adjustments[button_id]
    adjusted_returns = {k: v * scenario["multiplier"] for k, v in DEFAULT_RETURNS.items()}
    
    # 시나리오별 계산
    initial_amount = initial * 10000
    monthly_amount = monthly * 10000
    
    portfolio_df = calculate_portfolio_returns(allocations, adjusted_returns, initial_amount, monthly_amount, years)
    
    if portfolio_df.empty:
        return html.P("No data available")
    
    final_year_data = portfolio_df[portfolio_df['Year'] == years]
    total_value = final_year_data['Ending Balance'].sum()
    total_invested = final_year_data['Total Invested'].sum()
    
    # 시나리오 결과 표시
    result = html.Div([
        html.H5(f"{scenario['name']} Scenario", className="text-primary mb-3"),
        html.P(f"Final Portfolio Value: ₩{total_value:,.0f}"),
        html.P(f"Total Return: {(total_value/total_invested-1)*100:.1f}%"),
        html.P(f"Risk Level: {'High' if scenario['volatility'] > 1.5 else 'Moderate' if scenario['volatility'] > 1 else 'Normal'}"),
        html.Hr(),
        html.H6("Strategy for this scenario:"),
        html.Ul([
            html.Li("Increase bond allocation and reduce equity" if button_id == "scenario-bear" else 
                   "Maximize equity exposure and reduce cash" if button_id == "scenario-bull" else 
                   "Maintain balanced allocation"),
            html.Li("Consider defensive assets like gold" if button_id == "scenario-bear" else 
                   "Focus on growth stocks and emerging markets" if button_id == "scenario-bull" else 
                   "Regular rebalancing is sufficient"),
            html.Li("Keep higher cash reserves for opportunities" if button_id == "scenario-bear" else 
                   "Minimize cash holdings to maximize growth" if button_id == "scenario-bull" else 
                   "Standard emergency fund is adequate")
        ])
    ])
    
    return result

# 메인 실행
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run_server(host="0.0.0.0", port=port, debug=False)