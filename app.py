from flask import Flask, render_template, request
from flask_wtf import FlaskForm
from wtforms import IntegerField, SubmitField, DateField, FloatField
from wtforms.validators import DataRequired
import requests
import os
from datetime import datetime
import pandas as pd
import math

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_key')


class DebtForm(FlaskForm):
    initial_debt = FloatField('Initial Debt', validators=[DataRequired()])
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    end_date = DateField('End Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Calculate')


def get_inflation_data():
    url = "https://index.minfin.com.ua/ua/economy/index/inflation/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(e)
        return None

    tables = pd.read_html(response.content)
    data = tables[0]
    data_list = data.values.tolist()
    formatted_data = []
    for row in data_list:
        year = row[0]
        for month, index in enumerate(row[1:13], start=1):
            year_month = f"{year}.{month}"
            year_month = year_month.replace(".0", "")
            if isinstance(index, str):
                index = float(index.replace('%', '').replace(',', '.'))
            else:
                index = float(index)
            formatted_data.append([year_month, index / 10])
    return formatted_data


def calculate_total_debt(initial_debt, start_date, end_date, inflation_data):
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")
    inflation_index = 1
    penalty_days = (end_date - start_date).days
    for row in inflation_data:
        year_month, index = row
        date = datetime.strptime(year_month, "%Y.%m")
        if start_date <= date <= end_date:
            if math.isnan(index):
                continue
            inflation_index *= (index / 100)
    inflation_losses = initial_debt * (inflation_index - 1)
    penalty = initial_debt * 3 * penalty_days / 365 / 100
    total_debt = initial_debt + inflation_losses + penalty
    return round(total_debt, 2), round(inflation_losses, 2), round(penalty, 2)


@app.route('/', methods=['GET', 'POST'])
def index():
    debt_form = DebtForm(prefix="debt_form")
    total_debt = None
    inflation_losses = None
    penalty = None

    if debt_form.validate_on_submit():
        inflation_data = get_inflation_data()
        if inflation_data is None:
            return "Error: Could not get inflation data"
        initial_debt = debt_form.initial_debt.data
        start_date = debt_form.start_date.data.strftime("%Y-%m-%d")
        end_date = debt_form.end_date.data.strftime("%Y-%m-%d")
        total_debt, inflation_losses, penalty = calculate_total_debt(initial_debt, start_date, end_date, inflation_data)

    return render_template('index.html', debt_form=debt_form, total_debt=total_debt, inflation_losses=inflation_losses,
                           penalty=penalty)


if __name__ == '__main__':
    app.run(debug=True)
