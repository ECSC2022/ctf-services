from django.urls import path

from web import views

urlpatterns = [
   path('', views.index, name='index'),
    path('work_in_progress/', views.work_in_progress, name='work_in_progress'),
    path('render_graph_voltage/', views.render_graph_voltage, name='render_graph_voltage'),
    path('render_graph_voltage_svg/', views.render_graph_voltage_svg, name='render_graph_voltage_svg'),
    path('render_graph_current/', views.render_graph_current, name='render_graph_current'),
    path('render_graph_current_png/', views.render_graph_current_png, name='render_graph_current_png'),
    path('render_graph_frequency/', views.render_graph_frequency, name='render_graph_frequency'),
    path('render_graph_frequency_html/', views.render_graph_frequency_html, name='render_graph_frequency_html'),
    path('render_graph_phase_shift/', views.render_graph_phase_shift, name='render_graph_phase_shift'),
    path('render_graph_phase_shift_svg/', views.render_graph_phase_shift_svg, name='render_graph_phase_shift_svg'),
    path('render_graph_power/', views.render_graph_power, name='render_graph_power'),
    path('render_graph_power_png/', views.render_graph_power_png, name='render_graph_power_png'),
    path('render_settings/', views.render_settings, name='render_settings'),
    path('warning', views.warning, name='warning'),
    path('current_readings', views.current_readings, name='current_readings'),

]