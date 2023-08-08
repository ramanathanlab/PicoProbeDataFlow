# https://drive.google.com/open?id=0B5vxvuZBEEfTRGdXZ2NXUjNKUUk

# if __name__ == '__main__':
#
# -------------------------------------------------------------------
# Version -  Comments
# -------------------------------------------------------------------
# 2018060401 -  Initial Version
#               Based on Demo Code from Thomas Caswell at BNL called XRFMap.py
#               reads Numpy Arrays stored by HyperSpectralAnalyzer Program
# 2018060402 -  created a "position array" as needed by TC script
# 2018060603 -  clean up displaylayout  for AEM rather than XRF
# 2018061204 -  more display fixes for the spectrum
# 2018061305 -  add polygon selector
# 201904xx06 -  calibrated x-axis on spectrum
# -------------------------------------------------------------------


# import required libraries
# import csv
# import sys
# import time
# import scipy as sc
import numpy as np
import time
import numpy
import json
import matplotlib.gridspec as gridspec
import matplotlib.widgets as mwidgets
from matplotlib import path
import matplotlib.pyplot as plt


class AEMInteract(object):
    # 2018060502
    #   this is Thomas Caswell python XRFInteract script  with  modifications
    #   need to sort out what/how the various arguments relate to the data
    #   for now I've just simply created dummy parameters that work
    #   as well as change the display formatting and some colors that work
    #   better for AEM
    #
    def __init__(
        self, counts, positions, DataCubeParameters, fig=None, pos_order=None, norm=None
    ):
        #        print ("this print statuement is in  the init routine")
        #        for key,value in DataCubeParameters.items() :
        #            print (key, ": ", value)

        if pos_order is None:  # I don't know what this  does?
            pos_order = {"x": 0, "y": 1}
        # extract x/y data
        self.x_pos = xpos = positions[pos_order["x"]]
        self.y_pos = ypos = positions[pos_order["y"]]
        self.points = np.transpose((xpos.ravel(), ypos.ravel()))
        # zero out some arrays used for data.
        self.energy = np.zeros(DataCubeParameters["NChannels"])  # x axis = energy axis
        self.SDataX = np.zeros(DataCubeParameters["NChannels"])  # y axis = counts
        self.SDataY = np.zeros(DataCubeParameters["NChannels"])
        self.evchn = DataCubeParameters["XIncrement"]  # calibration for energy axis
        self.offset = DataCubeParameters["XOffset"]  # calibration for energy axis
        self.DataCubeParameters = DataCubeParameters
        # sort ouf the normalization
        #  I have no idea what this is doing
        if norm is None:
            norm = np.ones_like(self.x_pos)
        norm = np.atleast_3d(norm[:])  # is this finding the maximum value?

        self.counts = counts[
            :
        ]  # / norm  I want a sum spectrum not normalized I removed the /norm

        # this fills in the calibrated Energy Axis

        for Enchannel in range(0, DataCubeParameters["NChannels"]):
            self.energy[Enchannel] = (
                DataCubeParameters["XOffset"]
                + DataCubeParameters["XIncrement"] * Enchannel
            ) / 1000.0
        #       copy to internal arrays
        self.SDataX = self.energy  # this is redundant
        #        self.SDataY=self.counts
        #        print (Enchannel, self.energy [Enchannel])

        # compute values we will use for extents below
        dx = np.diff(xpos.mean(axis=0)).mean()
        dy = np.diff(ypos.mean(axis=1)).mean()
        left = xpos[:, 0].mean() - dx / 2
        right = xpos[:, -1].mean() + dx / 2
        top = ypos[0].mean() - dy / 2
        bot = ypos[-1].mean() + dy / 2

        # create a figure if we must
        if fig is None:
            import matplotlib.pyplot as plt

            fig = plt.figure(
                tight_layout=True, figsize=(15, 5)
            )  # I like bigger figures added fig size
        # clear the figure
        fig.clf()
        # set the window title (look at the tool bar)
        # fig.canvas.set_window_title('HyperCubeData Import from Numpy Format') # retitlted to AEM from XRF
        self.fig = fig
        # set up the figure layout
        gs = gridspec.GridSpec(1, 2)  # changed the layout to horizontal from vertical

        # set up the top/left panel (the map)
        self.ax_im = fig.add_subplot(gs[0, 0], gid="imgmap")
        self.ax_im.set_xlabel("x [pixel]")
        self.ax_im.set_ylabel("y [pixel]")
        self.ax_im.set_title(
            "period-click = 1 pixel, "
            "alt-click = polygon, @-click = lasso, "
            "right-click to reset"
        )

        # this is the image graphic

        # show the initial image
        self.im = self.ax_im.imshow(
            self.counts[:, :, :].sum(axis=2),
            cmap="Blues_r",  #'viridis', # I don't like viridis for spectral images
            interpolation="nearest",
            extent=[left, right, bot, top],
        )
        # and colorbar
        self.cb = self.fig.colorbar(self.im, ax=self.ax_im)

        # and the ROI mask (overlay in red)
        self.mask = np.ones(self.x_pos.shape, dtype="bool")
        self.mask_im = self.ax_im.imshow(
            self._overlay_image,
            interpolation="nearest",
            extent=[left, right, bot, top],
            zorder=self.im.get_zorder(),
        )
        self.mask_im.mouseover = False  # do not consider for mouseover text

        # this is the spectral graphic

        # set up the lower/right axes (the average spectrum of the ROI)
        self.ax_spec = fig.add_subplot(gs[0, 1], gid="spectrum")
        self.ax_spec.set_ylabel("XEDS counts")
        self.ax_spec.set_xlabel("Energy (keV)")
        self.ax_spec.set_yscale("log")
        #        yspecmin=0.001 # I don't know how this computes the limits for log scales
        #        yspecmax=1000 # I don't know how this computes the limits for log scales
        #        self.ax_spec.set_ylim(yspecmin,yspecmax)
        self.ax_spec.set_title("click-and-drag to select energy region")
        self._EROI_txt = self.ax_spec.annotate(
            "ROI: all",
            xy=(0, 1),
            xytext=(0, 5),
            xycoords="axes fraction",
            textcoords="offset points",
        )
        self._pixel_txt = self.ax_spec.annotate(
            "HSImage average",
            xy=(1, 1),
            xytext=(0, 5),
            xycoords="axes fraction",
            textcoords="offset points",
            ha="right",
        )

        # set up the spectrum, to start average everything
        (self.spec,) = self.ax_spec.plot(
            self.energy[:], self.counts[:, :, :].sum(axis=(0, 1)), lw=2
        )
        # @@@@@@@@@@@        self.SDataY=self.counts[:,:,:].sum(axis=(0,1)) # trying to copy the spectral data to the SDataY array
        #        self.spec, = self.ax_spec.plot(self.counts[:,:,:].sum(axis=(0,1)), lw=2)  # this was original uncalibrated x axis

        # set up the selector widget for the spectrum
        self.selector = mwidgets.SpanSelector(
            self.ax_spec,
            self._on_span,
            "horizontal",
            useblit=True,
            minspan=0.01,
            # span_stays=True,
        )
        # placeholder for the lasso & polygon selector
        self.lasso = None
        self.polygon = None
        # hook up the mouse events for the XRF map
        self.cid = self.fig.canvas.mpl_connect("button_press_event", self._on_click)

    @property
    def _overlay_image(self):
        ret = np.zeros(self.mask.shape + (4,), dtype="uint8")
        if np.all(self.mask):
            return ret
        ret[:, :, 0] = 255
        ret[:, :, 3] = 100 * self.mask.astype("uint8")
        return ret

    def _on_click(self, event):
        # not in the right axes, bail
        ax = event.inaxes
        if ax is None or ax.get_gid() != "imgmap":
            return
        # if right click, clear ROI
        if event.button == 3:
            return self._reset_spectrum()
        if event.key == "e":
            return self._polygon_disconnect()

        # if alt, start polygon
        if event.key == "alt":
            return self._polygon_on_press(event)
        if event.key == "@":
            return self._lasso_on_press(event)
        # if shift, select a pixel
        if event.key == ".":
            return self._pixel_select(event)

    def _reset_spectrum(self):
        self.mask = np.ones(self.x_pos.shape, dtype="bool")
        self.mask_im.set_data(self._overlay_image)
        new_y_data = self.counts[:, :, :].sum(
            axis=(0, 1)
        )  # I want the sum spectrum not a mean
        self.SDataY = self.counts[:, :, :].sum(axis=(0, 1))
        #        self._pixel_txt.set_text('map average')
        self.ax_spec.relim()
        # self.ax_spec.autoscale(True, axis='y')
        self.fig.canvas.draw_idle()

    def _pixel_select(self, event):
        x, y = event.xdata, event.ydata
        # get index by assuming even spacing
        # TODO use kdtree?
        diff = np.hypot((self.x_pos - x), (self.y_pos - y))
        y_ind, x_ind = np.unravel_index(np.argmin(diff), diff.shape)

        # get the spectrum for this point
        new_y_data = self.counts[y_ind, x_ind, :]
        self.mask = np.zeros(self.x_pos.shape, dtype="bool")
        self.mask[y_ind, x_ind] = True
        self.mask_im.set_data(self._overlay_image)
        self._pixel_txt.set_text(
            "pixel: [{:d}, {:d}] ({:.3g}, {:.3g})".format(
                y_ind, x_ind, self.x_pos[y_ind, x_ind], self.y_pos[y_ind, x_ind]
            )
        )

        self.spec.set_ydata(new_y_data)
        self.SDataY = new_y_data
        self.ax_spec.relim()
        self.ax_spec.autoscale(True, axis="y")
        self.fig.canvas.draw_idle()

    def _on_span(self, vmin, vmax):
        #        evchn=5 #DataCubeParameters['XIncrement']
        #        offset=-479.0021 #DataCubeParameters['XOffset']
        cmin = (vmin * 1000.0 - self.offset) / self.evchn  # calculate the channel value
        cmax = (vmax * 1000.0 - self.offset) / self.evchn  # calcualte the channel value
        #        print ("vmin, vmax, evch, offset, cmin, cmax",vmin,vmax,self.evchn,self.offset, cmin,cmax)
        print("Energy Window (keV): {0:8.2f} - {1:8.2f}".format(vmin, vmax))

        cvmin, cvmax = map(int, (cmin, cmax))
        #        print (cmin,cmax,cvmin,cvmax)
        new_image = self.counts[:, :, cvmin:cvmax].sum(axis=2)
        new_max = new_image.max()
        self._EROI_txt.set_text("ROI[E] = {0:5.2f} :{1:5.2f}".format(vmin, vmax))
        self.im.set_data(new_image)
        self.im.set_clim(0, new_max)
        self.fig.canvas.draw_idle()

    def _lasso_on_press(self, event):
        self.lasso = mwidgets.Lasso(
            event.inaxes, (event.xdata, event.ydata), self._lasso_call_back
        )

    def _lasso_call_back(self, verts):
        p = path.Path(verts)

        new_mask = p.contains_points(self.points).reshape(*self.x_pos.shape)
        self.mask = new_mask
        self.mask_im.set_data(self._overlay_image)
        #        new_y_data = self.counts[new_mask].mean(axis=0)
        new_y_data = self.counts[new_mask].sum(axis=0)
        self.spec.set_ydata(new_y_data)
        self.SDataY = new_y_data
        self.ax_spec.relim()
        self.ax_spec.autoscale(True, axis="y")
        self.fig.canvas.draw_idle()

    def _polygon_on_press(self, event):
        #        self.lineprops = dict(color='r', linestyle='-',linewidth = 2)
        #        self.markerprops = dict(markersize=7)
        self.polygon = mwidgets.PolygonSelector(
            event.inaxes, self._polygon_call_back, vertex_select_radius=10
        )  # #self.lineprops, self.markerprops)

    def _polygon_disconnect(self, event):
        #        self.lineprops = dict(color='r', linestyle='-',linewidth = 2)
        #        self.markerprops = dict(markersize=7)
        self.polygon.disconnect_events()
        self.fig.canvas.draw_idle()

    def _polygon_call_back(self, verts):
        p = path.Path(verts)

        new_mask = p.contains_points(self.points).reshape(*self.x_pos.shape)
        self.mask = new_mask
        self.mask_im.set_data(self._overlay_image)
        #        new_y_data = self.counts[new_mask].mean(axis=0)
        new_y_data = self.counts[new_mask].sum(axis=0)
        self.spec.set_ydata(new_y_data)
        self.SDataY = new_y_data
        self.ax_spec.relim()
        self.ax_spec.autoscale(True, axis="y")
        self.fig.canvas.draw_idle()


# ------------------------------------------------------------------------------
# My AEM related code starts here
# ------------------------------------------------------------------------------


def openfile_dialog(DataDirPath, fileextension):
    #
    # this routine implements  a dialog box to get the data file
    #
    from PyQt5 import QtGui
    from PyQt5 import QtGui, QtWidgets

    if DataDirPath == "":
        DataDirPath = "./"
    # ,---This line must be commented out otherwise program locks up
    app = QtWidgets.QApplication([dir])
    fname = QtWidgets.QFileDialog.getOpenFileName(
        None, "Select a file...", DataDirPath, filter="*." + str(fileextension)
    )  # filter="All files (*)")
    return str(fname[0])


# Version Record
NJZCode_Version = "2019042206"

# some info on the screen

print("\n\n\n\n")
print("*******************************************************************")
print("HyperSpectral Data Display Program for Numpy Files- Version: ", NJZCode_Version)
print("uses Python routines from Tom Caswell of Brookhaven National Lab")
print("*******************************************************************")

print("Be patient! This is a slow program, when used with large HSI data sets;-)")

#
# definitions
#
# I am going to plot some data so I'm zeroing some arrays
#
# There will be code below that is not needed for this script
# it is copied from other routines, that also display NP HyperDataCubes
# but it will be used later when I figure out how to add other functionality
#
TotalChannelMax = 4100
LowEnergy = 0  # non-zero default
HighEnergy = 10  # non-zero default value
SDataX_Mem = np.zeros(
    TotalChannelMax
)  # create an empty Energy list for Spectral energy (x) axis
SDataY_Mem = np.zeros(
    TotalChannelMax
)  # create an empty Energy list for Spectral data  (y) axis
SImage_Mem = np.zeros((1, 1))  # create an empty SI 2D Array
SData = [0]  # create a Intensity List

Spectrum_Data_Dimensions = TotalChannelMax
# Spectrum_Data_Dimensions[0]=TotalChannelMax# this is a default value

try:  # this is a simple test routine  to see if a Data Path Exists
    DataDirPath
except NameError as err:
    DataDirPath = "./"


# DataDirPath="./" # to avoid errors when  read in the data files
#
# get a Numpy data file , which was created by my other HSI data translator scripts
#
print("\nSelect Numpy (.npy) File")

# Open and Read  file via python scripts


FileName = openfile_dialog(DataDirPath, "npy")
plt.pause(
    2
)  # this to give the program some time to catchup. this is needed for the dialog box to close

# strip out the file name and Directory Path.

FileSName = str.split(FileName, "/")
FNlength = len(FileSName) - 1  # file name should be the last element
FLen = len(FileName)
DLen = FileName.rfind("/")
dwidth = FLen - DLen
Directory = FileName.rjust(dwidth)
DataDirPath = FileName.rstrip(FileSName[FNlength])


HyperCubeData = numpy.load(FileName, "r")  # this is the local file reference name

#
# read in the Parameter file for this data set this would havealso been created by the translator scripts
#

ParamFile = open(
    FileName + ".dict", "r"
)  # I defined this parameter file it is created by the translator
Param_Mem = json.load(ParamFile)
ParamFile.close()

plt.rcParams["toolbar"] = "toolbar2"
plt.pause(
    2
)  # this to give the program some time to catchup. this is needed for the dialog box to close


# print(Param_Mem)  # this just writes the Parameter Dictionary to the screen

print("\n HyperSpectral Parameters")
print(" ------------------------\n")
for key, value in Param_Mem.items():
    print(key, ": ", value)


# ans=input("<CR> to continue")

# print ("HyperCubeData Dimensions : [",HyperCubeData.shape[0]," x ", HyperCubeData.shape[1]," x ", HyperCubeData.shape[2]," ] ") # this is the shape info of the file
# print (HyperCubeData.dtype,HyperCubeData.shape) # this is the shape info of the file

XDimension = HyperCubeData.shape[0]
YDimension = HyperCubeData.shape[1]

try:
    ZDimension = HyperCubeData.shape[
        2
    ]  # if this value is non-zero then it is a 3D cube otherwise it is a 2D image

except:
    ZDimension = 0
    print(
        "HyperCubeData Dimensions : [",
        HyperCubeData.shape[0],
        " x ",
        HyperCubeData.shape[1],
        " ] ",
    )  # this is the shape info of the file
    print("This was a 2D Data File\n Plotting the Image")
    # now draw it to the screen
    SImage = HyperCubeData
    fig = plt.figure(num=FileSName[FNlength], figsize=(4, 3))
    plt.clf()
    plt.axes([0, 0, 1, 1])  # makes this full scale to figsize
    plt.xticks([]), plt.yticks([])  # this turns off tick marks
    plt.imshow(SImage, cmap="gray", origin="upper")  # what to plot
    plt.colorbar(shrink=0.9)
    plt.show()  # draw it\
#    exit()
if ZDimension != 0:  # this is a 3D cube
    # this is a data cube
    print(
        "\nHyperCubeData Dimensions : [",
        HyperCubeData.shape[0],
        " x ",
        HyperCubeData.shape[1],
        " x ",
        HyperCubeData.shape[2],
        " ] ",
    )  # this is the shape info of the file

    print("Opening File for Analysis")
    FSize = XDimension * YDimension * ZDimension
    if FSize > 1e9:
        print("This is a large file ", 2 * FSize / 1e9, "Gb it will take time")  #
    # create a 2axis array of positions x,y
    # this array is used by TC's script
    # if it does not exist the script fails
    # I don't understand the dimensionality of this array, but to get
    # TC's script to work it must be like this
    # likely due to how the BNL data is written
    #

    starttime = time.time()  # I'm curious how long this takes for different files

    XYpositionarray = np.empty(
        shape=(2, XDimension, YDimension)
    )  # the shape of the position array
    indexx = 0  # for now just create positions by pixel.  Later we can add dimesnions
    indexy = 0
    #
    # will also need to create dimensions for the spectra it is in the Param File
    # just need to incorporate it into a modified version of TC's script which uses "channels/bins"
    #
    for indexx in range(0, XDimension):
        XYpositionarray[0, indexx, indexy] = indexy
        XYpositionarray[1, indexx, indexy] = indexx
        for indexy in range(0, YDimension):
            XYpositionarray[0, indexx, indexy] = indexy
            XYpositionarray[1, indexx, indexy] = indexx

    #   this is my abbreviated call to the Interact Routine, I have omitted several kwargs

    AEMGraphicObject = AEMInteract(HyperCubeData, XYpositionarray, Param_Mem)

    #   this is the original format of TC's call to the routine from an HDF5 file
    #   xrf = XRFInteract(g['detsum']['counts'][:], g['positions']['pos'][:],
    #                  norm=g['scalers']['val'][:, :, 0])
    #   I don't know what the actual kwargs mean but the code works without them

    #
    #   remember you now have a Python object you get it's components by specifying them
    #
    # this is a one time read need a loop or something to write it to a file or to update the python variable.
    SDataX_Mem = (
        AEMGraphicObject.SDataX
    )  # this is a one time read need a loop or something to write it to a file
    SDataY_Mem = AEMGraphicObject.SDataY

    endtime = time.time()
    seconds = endtime - starttime
    minutes = seconds / 60
    print(
        "\nEnd of Hyper Cube Data Reconstruction \nElapsed Time = ",
        minutes,
        " minutes ",
    )
# un comment out this line to use 'interacitve' mode
# plt.ion()
plt.show()
