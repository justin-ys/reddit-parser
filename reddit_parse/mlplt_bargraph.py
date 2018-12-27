import numpy
import matplotlib
import matplotlib.pyplot as plt
from PIL import Image

matplotlib.rcParams.update({'font.size': 22})
#from: http://www.icare.univ-lille1.fr/tutorials/convert_a_matplotlib_figure
def fig2data(fig):
    """
    @brief Convert a Matplotlib figure to a 4D numpy array with RGBA channels and return it
    @param fig a matplotlib figure
    @return a numpy 3D array of RGBA values
    """
    # draw the renderer
    fig.canvas.draw()

    # Get the RGBA buffer from the figure
    w, h = fig.canvas.get_width_height()
    buf = numpy.fromstring(fig.canvas.tostring_argb(), dtype=numpy.uint8)
    buf.shape = (w, h, 4)

    # canvas.tostring_argb give pixmap in ARGB mode. Roll the ALPHA channel to have it in RGBA mode
    buf = numpy.roll(buf, 3, axis=2)
    plt.close()
    return buf

def fig2img ( fig ):
    """
    @brief Convert a Matplotlib figure to a PIL Image in RGBA format and return it
    @param fig a matplotlib figure
    @return a Python Imaging Library ( PIL ) image
    """
    # put the figure pixmap into a numpy array
    buf = fig2data(fig)
    w, h, d = buf.shape
    return Image.frombytes("RGBA", (w,h), buf.tostring())

#end from

def graph_names(names: list, values: list, title="") -> Image:
    """Given a set of names and values,
    makes a simple  horizontal bargraph with
    line ticks and returns the path the resulting
    image.
    Argument names: The names of the labels
    Argument values: The lengths of the bars
    Argument title: The title for the graph."""
    fig = plt.figure(figsize=(26,3))
    fig.patch.set_facecolor('none')

    ticks = numpy.arange(len(values)) # even spacing!

    plt.barh(ticks,
             values,
             tick_label=names,
             height=0.5)  # probably shouldn't be hardcoded

    plt.title(title)

    return fig2img(plt.gcf())


if __name__ == '__main__':
    img = graph_names(['john', 'doe', 'freeman'], [17,14,24])
    img.show()
