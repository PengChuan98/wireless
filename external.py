# -*- coding: utf-8 -*-
# @Time    : 2020/11/26 15:16

# here put the import lib
import time

import matplotlib.pyplot as plt
from mpl_toolkits.axisartist.parasite_axes import HostAxes, ParasiteAxes

HIGH = 8
WIDTH = 50


def draw_save(data_time, data_through, data_rssi, data_attn, data_interval=1, time_interval=50,
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
    host.set_xlabel("x axes")
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


if __name__ == '__main__':
    import numpy as np

    data = np.loadtxt("test.txt", delimiter=",", dtype=str, encoding='utf-8')
    draw_save(np.array(data[:, 0]).tolist(), np.array(data[:, 1], dtype=float).tolist(),
              np.array(data[:, 2], dtype=float).tolist(),
              list(map(lambda x: -x, np.array(data[:, 3], dtype=float).tolist())), 1, 100)
    # import time
    #
    # date = time.strftime("%H:%M:%S")
    # print(date)
