import base64
import hashlib
import os
from io import BytesIO

from bokeh.io import output_file, save, curdoc
from bokeh.io.export import get_screenshot_as_png
from bokeh.themes import Theme
from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse

from .models import DataLog
from svg.charts import time_series
import matplotlib.pyplot as plt
import datetime
import numpy as np
from bokeh.plotting import figure, show

default_counts = {
    "voltage": 10,
    "current": 10,
    "frequency": 10,
    "phase_shift": 10,
    "power": 10
}
limit_counts = {
    "voltage": 10, # 10 is the maximum as lib is super-duper slow....
    "current": 100,
    "frequency": 100,
    "phase_shift": 10, # 10 is the maximum as lib is super-duper slow....
    "power": 100
}
# Create your views here.


def get_setting_count(request, setting):
    # get settings from session, check if limits from limit_counts are followed, use default from default_counts,
    # save at the end
    setting_count = request.session.get(f"{setting}_count", default_counts[setting])
    if setting_count < 1:
        messages.error(request, "Count must be larger than 0")
        setting_count = default_counts[setting]
    if setting_count > limit_counts[setting]:
        messages.error(request, "Count must not be more than {}".format(limit_counts[setting]))
        setting_count = limit_counts[setting]
    request.session[f"{setting}_count"] = setting_count
    return setting_count


def index(request):
    return render(request, '_base.html')


def warning(request):
    return render(request, 'warnings.html')


# generate a function to serve file work_in_progress.html
def work_in_progress(request):
    return render(request, 'work_in_progress.html', context={'title': 'Work in Progress'})


# generate a function to serve file graph.html with image data link to corresponding svg file
def render_graph_voltage(request):
    image_data = reverse('render_graph_voltage_svg')
    return render(request, 'graph.html', context={'title': 'Voltage', 'image_data': image_data})


# generate a function to render a graph from variable voltage using library svg.charts
def render_graph_voltage_svg(request):
    setting_count = get_setting_count(request, "voltage")
    logs_ = list(DataLog.objects.order_by('-timestamp')[:100])  # get the latest 100 log entries
    if len(logs_) < 2:
        messages.error(request, "Not enough data to generate graph")
        return HttpResponse("Not enough data to generate graph")
    logs = logs_[:setting_count]  # get the last setting_count logs
    data = []
    for l in logs:
        data.append(l.timestamp.strftime("%m/%d/%Y %H:%M:%S"))
        data.append(l.voltage)
    g = time_series.Plot({"no_css": False})
    g.css_inline = True
    g.timescale_divisions = '3 minutes'
    g.stagger_x_labels = False
    g.show_data_labels = False
    g.x_label_format = '%H:%M'
    # g.max_y_value = 200

    g.add_data(
        {
            'data': data,
            'title': 'Voltage',
        }
    )
    burned = g.burn()
    burned = burned.replace("fill:#000", "fill:black").replace("fill:#fff", "fill:#00aaaa"). \
        replace("fill:#f0f0f0", "fill:#000084").replace("stroke:#f00", "stroke:#00aaaa"). \
        replace("stroke:#666", "stroke:#000084")
    return HttpResponse(burned, content_type="image/svg+xml")


def render_graph_current(request):
    image_data = reverse('render_graph_current_png')
    return render(request, 'graph.html', context={'title': 'Current', 'image_data': image_data})


# generate a function to render a graph from variable current using library matplotlib
def render_graph_current_png(request):
    setting_count = get_setting_count(request, "current")
    logs_ = list(DataLog.objects.order_by('-timestamp')[:100])  # get the latest 100 log entries
    if len(logs_) < 2:
        messages.error(request, "Not enough data to generate graph")
        return HttpResponse("Not enough data to generate graph")
    logs = logs_[:setting_count]  # get the last 10 logs
    x = []
    y = []
    for l in logs:
        x.append(l.timestamp)
        y.append(l.current)

    x = np.array(x)
    y = np.array(y)
    plt.rcParams["figure.figsize"] = (12, 5)

    plt.figure(facecolor='#00aaaa')
    plt.rcParams.update({'text.color': "#00aaaa",
                         'axes.labelcolor': "#00aaaa"})
    plt.plot(x, y, color='#00aaaa', markersize=1)
    ax = plt.gca()
    ax.set_xlabel('Time', color="#000084")
    ax.set_ylabel('Current', color="#000084")
    ax.set_facecolor('#000084')

    tmpfile = BytesIO()
    plt.savefig(tmpfile, format='png')
    return HttpResponse(tmpfile.getvalue(), content_type="image/png")


def render_graph_frequency(request):
    image_data = reverse('render_graph_frequency_html')
    return render(request, 'graph_html.html', context={'title': 'Frequency', 'image_data': image_data})


# generate a function to render a graph from variable frequency using library bokeh
def render_graph_frequency_html(request):
    setting_count = get_setting_count(request, "frequency")
    logs_ = list(DataLog.objects.order_by('-timestamp')[:100])  # get the latest 100 log entries
    if len(logs_) < 2:
        messages.error(request, "Not enough data to generate graph")
        return HttpResponse("Not enough data to generate graph")
    logs = logs_[:setting_count]  # get the last 10 logs
    x = []
    y = []
    for l in logs:
        x.append(l.timestamp)
        y.append(l.frequency)

    curdoc().theme = Theme(filename=os.path.dirname(os.path.abspath(__file__)) + "/bokeh_style.yml")
    p = figure(title="Frequency", x_axis_label='x', y_axis_label='Frequency', x_axis_type='datetime')

    p.line(x, y, legend_label="Frequency", line_width=2)

    output_file(filename="/tmp/custom_filename.html", title="iFrame")
    save(p)

    return HttpResponse(open('/tmp/custom_filename.html', 'br').read(), content_type="text/html")


# generate a function to serve file graph.html with image data link to corresponding svg file
def render_graph_phase_shift(request):
    image_data = reverse('render_graph_phase_shift_svg')
    return render(request, 'graph.html', context={'title': 'Phase Shift', 'image_data': image_data})


# generate a function to render a graph from variable phase_shift using library svg.charts
def render_graph_phase_shift_svg(request):
    setting_count = get_setting_count(request, "phase_shift")
    logs_ = list(DataLog.objects.order_by('-timestamp')[:100])  # get the latest 100 log entries
    if len(logs_) < 2:
        messages.error(request, "Not enough data to generate graph")
        return HttpResponse("Not enough data to generate graph")
    logs = logs_[:setting_count]  # get the last 10 logs
    data = []
    for l in logs:
        data.append(l.timestamp.strftime("%m/%d/%Y %H:%M:%S"))
        data.append(l.phase_shift)
    g = time_series.Plot({"no_css": False})
    g.css_inline = True
    g.timescale_divisions = '3 minutes'
    g.stagger_x_labels = False
    g.show_data_labels = False
    g.x_label_format = '%H:%M'
    # g.max_y_value = 200

    g.add_data(
        {
            'data': data,
            'title': 'Phase Shift',
        }
    )
    burned = g.burn()
    burned = burned.replace("fill:#000", "fill:black").replace("fill:#fff", "fill:#00aaaa"). \
        replace("fill:#f0f0f0", "fill:#000084").replace("stroke:#f00", "stroke:#00aaaa"). \
        replace("stroke:#666", "stroke:#000084")
    return HttpResponse(burned, content_type="image/svg+xml")


def render_graph_power(request):
    image_data = reverse('render_graph_power_png')
    return render(request, 'graph.html', context={'title': 'Power', 'image_data': image_data,
                                                  "additional_style": "width: 100%; height: 500px;" })


# generate a function to render a graph from variables apparent_power, reactive_power,
# active_power using library matplotlib
def render_graph_power_png(request):
    setting_count = get_setting_count(request, "power")
    logs_ = list(DataLog.objects.order_by('-timestamp')[:100])  # get the latest 100 log entries
    if len(logs_) < 2:
        messages.error(request, "Not enough data to generate graph")
        return HttpResponse("Not enough data to generate graph")
    logs = logs_[:setting_count]  # get the last 10 logs
    x = []
    y = {
        'apparent_power': [],
        'reactive_power': [],
        'active_power': [],
    }
    for l in logs:
        x.append(l.timestamp)
        y["apparent_power"].append(l.apparent_power)
        y["reactive_power"].append(l.reactive_power)
        y["active_power"].append(l.active_power)

    x = np.array(x)
    y_ap = np.array(y["apparent_power"])
    y_rp = np.array(y["reactive_power"])
    y_acp = np.array(y["active_power"])
    plt.rcParams["figure.figsize"] = (12, 5)

    plt.figure(facecolor='#00aaaa')
    plt.rcParams.update({'text.color': "#00aaaa",
                         'axes.labelcolor': "#00aaaa"})
    plt.plot(x, y_ap, color='#ff5', markersize=1, label="apparent_power")
    plt.plot(x, y_rp, color='#f55', markersize=1, label="reactive_power")
    plt.plot(x, y_acp, color='#00aaaa', markersize=1, label="active_power")
    ax = plt.gca()
    ax.set_xlabel('Time', color="#000084")
    ax.set_facecolor('#000084')
    ax.legend(['Apparent Power', 'Reactive Power', "Active Power"])

    tmpfile = BytesIO()
    plt.savefig(tmpfile, format='png')
    return HttpResponse(tmpfile.getvalue(), content_type="image/png")


# render settings.html
def render_settings(request):
    resp = render(request, 'settings.html', context={'title': 'Settings', "numbers": range(0, 100),
                                                     'settings': default_counts.keys()})
    if request.method == 'POST':
        setting = request.POST.get('setting')
        if setting not in default_counts.keys():
            messages.error(request, f"Invalid setting {setting}")
            return resp
        value = request.POST.get(setting)
        if not value.isdigit():
            messages.error(request, f"Invalid value {value}")
            return resp
        request.session[f"{setting}_count"] = int(value)
    return resp


def current_readings(request):
    values = DataLog.objects.order_by('-timestamp').first()
    if not values:
        messages.error(request, "We havent received any data yet")
        return render(request, 'index.html', context={'title': 'Current Readings', "text": "We havent received any data yet"})
    values = values.to_dict()
    print(values["_raw"])
    sha_hash = hashlib.md5()
    sha_hash.update(values["_raw"].encode('utf-8'))
    values["hash"] = sha_hash.hexdigest()
    del values["_raw"]
    return render(request, 'current_readings.html', context={'title': 'Current Readings', "values": values})