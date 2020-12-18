# -*- coding: utf-8 -*-
# @Time    : 2020/11/26 15:16

# here put the import lib
import math
import matplotlib.pyplot as plt
from mpl_toolkits.axisartist.parasite_axes import HostAxes, ParasiteAxes
from matplotlib.ticker import MultipleLocator, FormatStrFormatter

HIGH = 8
WIDTH = 50


def draw_save_Obsolete(data_time, data_through, data_rssi, data_attn, data_interval=1, time_interval=1,
                       title="time/through/rssi/attn", save_path="logging.png"):
    x_labels = data_time
    x_ticks = [i for i in range(len(x_labels))][::data_interval]
    through = data_through[::data_interval]
    rssi = data_rssi[::data_interval]
    attn = data_attn[::data_interval]

    fig = plt.figure(figsize=(WIDTH, HIGH))

    host = HostAxes(fig, [0.15, 0.1, 0.65, 0.8])
    parasite = ParasiteAxes(host, sharex=host)

    host.parasites.append(parasite)

    host.axis['right'].set_visible(False)
    parasite.axis['right'].set_visible(True)

    host.set_ylabel("Through")
    host.set_xlabel("TIME")
    parasite.set_ylabel("Rssi/Attn")

    parasite.axis['right'].major_ticklabels.set_visible(True)
    parasite.axis['right'].label.set_visible(True)

    fig.add_axes(host)

    host.set_ylim(0, 60.)
    host.set_xlim(x_ticks[0], x_ticks[-1])
    parasite.set_ylim(-100, 0)

    x_tick = x_ticks[::time_interval]
    x_label = x_labels[::time_interval]
    host.set_xticks(x_tick)
    host.set_xticklabels(tuple(x_label), rotation=45)

    line_through, = host.plot(x_ticks, through, "b-", label="Through")
    line_attn, = parasite.plot(x_ticks, attn, "g-", label="Attn")
    line_rssi, = parasite.plot(x_ticks, rssi, "r-", label="Rssi")

    host.set_title(title, fontsize=25, color='r')

    fig.canvas.print_figure(save_path)
    plt.show()


def draw_save(data_time, data_through, data_rssi, data_attn, data_interval=1, time_interval=20,
                        title="time/through/rssi/attn", save_path="logging.png"):
    x_labels = data_time
    x_ticks = [i for i in range(len(x_labels))][::data_interval]
    through = data_through[::data_interval]
    rssi = data_rssi[::data_interval]
    attn = data_attn[::data_interval]

    fig = plt.figure(figsize=(WIDTH, HIGH))

    host = fig.add_subplot(111)
    parasite = plt.twinx()

    host.set_ylabel("Through", fontsize=20)
    host.set_xlabel("Time", fontsize=20)
    parasite.set_ylabel("Rssi/Attn", fontsize=20)

    host.set_ylim(0, 60.)
    host.set_xlim(x_ticks[0], x_ticks[-1])
    parasite.set_ylim(-100, 0)

    x_tick = x_ticks[::time_interval]
    x_label = x_labels[::time_interval]
    host.set_xticks(x_tick)
    host.set_xticklabels(tuple(x_label), rotation=90, fontsize=8)

    line_through, = host.plot(x_ticks, through, "b-", label="Through")
    line_attn, = parasite.plot(x_ticks, attn, "g-", label="Attn")
    line_rssi, = parasite.plot(x_ticks, rssi, "r-", label="Rssi")

    host.set_title(title, fontsize=25, color='r')
    host.grid()

    plt.legend([line_through, line_attn, line_rssi], ["Through", "Attn", "Rssi"])
    fig.canvas.print_figure(save_path)
    plt.show()


def smooth():
    # TODO:Spline interpolation
    pass


def max_list(list_value):
    temp = list_value[0]
    for i in list_value:
        temp = temp if temp > i else i
    return temp


def draw_save_Obsolete2(data_time, data_through, data_rssi, data_attn, data_interval=1, time_interval=None,
              title="time/through/rssi/attn", save_path="logging.png"):
    x_labels = data_time
    x_ticks = [i for i in range(len(x_labels))][::data_interval]
    through = data_through[::data_interval]
    rssi = data_rssi[::data_interval]
    attn = data_attn[::data_interval]

    fig = plt.figure(figsize=(WIDTH, HIGH))
    ax = fig.add_subplot(111)

    # x axis label and ticks
    time_interval = math.ceil(len(x_ticks) / 100) if time_interval is None else time_interval
    x_tick = x_ticks[::time_interval]
    x_label = x_labels[::time_interval]
    ax.set_xticks(x_tick)
    ax.set_xticklabels(tuple(x_label), rotation=90, fontsize=8)

    # y ticks
    y_major_locator = MultipleLocator(5)
    y_major_label_format = FormatStrFormatter('%.0f')
    y_minor_locator = MultipleLocator(1)

    # y axis label and ticks
    ax.yaxis.set_major_locator(y_major_locator)
    ax.yaxis.set_major_formatter(y_major_label_format)
    ax.yaxis.set_minor_locator(y_minor_locator)

    # config ax type
    ax.set_title(title, fontsize=25, color='r')
    ax.set_ylabel("Through/Rssi/Attn", fontsize=20)
    ax.set_xlabel("Time", fontsize=20)
    ax.set_ylim(0, max_list([np.max(through), np.max(rssi), np.max(attn)]) + 10)
    ax.set_xlim(x_ticks[0], x_ticks[-1])
    ax.xaxis.grid(True)
    ax.yaxis.grid(True, which="major")
    ax.spines['top'].set_visible(True)
    ax.spines['right'].set_visible(True)

    line_through, = ax.plot(x_ticks, through, "black", label="Through")
    line_attn, = ax.plot(x_ticks, attn, "r-", label="Attn")
    line_rssi, = ax.plot(x_ticks, rssi, "b-", label="Rssi")
    plt.legend([line_through, line_attn, line_rssi], ["Through", "Attn", "Rssi"])
    # plt.legend([line_through, line_attn, line_rssi], ["Through", "Attn", "Rssi"], loc=1)
    fig.canvas.print_figure(save_path)
    plt.show()


"""
ax1.grid(axis="x")

line_through, = ax1.plot(x_ticks, through, "black", label="Through")
line_attn, = ax1.plot(x_ticks, attn, "r-", label="Attn")
print(rssi)
line_rssi, = ax1.plot(x_ticks, rssi, "b-", label="Rssi")

ax1.spines['top'].set_visible(False)
ax1.spines['right'].set_visible(False)
"""

if __name__ == '__main__':
    import numpy as np

    data = np.loadtxt("test.txt", delimiter=",", dtype=str)
    draw_save(np.array(data[:, 0]).tolist(), np.array(data[:, 1], dtype=float).tolist(),
              list(map(lambda x: -x, np.array(data[:, 2], dtype=float).tolist())),
              np.array(data[:, 3], dtype=float).tolist(), 1, 20, title="")
