import numpy as np
import matplotlib.pyplot as plt

from telluric.util.raster_utils import _join_masks_from_masked_array

from .base_renderer import BaseFactory


class ProductView():
    """ ProductView is an abstract class.

    To implement a view class you should inherit from one of its subclasses, ColormapView or BandsComposer.
    You should set the following attributes if it is not set in the parent class:
        name display_name description type output_bands required_bands
    """

    type = np.uint8

    @classmethod
    def get_name(cls):
        return cls.name

    @classmethod
    def to_dict(cls):
        attributes = "name display_name description type output_bands required_bands".split()
        d = {}
        for attr in attributes:
            d[attr] = getattr(cls, attr)
        return d


# see http://matplotlib.org/examples/color/colormaps_reference.html for cmaps catalog
class ColormapView(ProductView):
    required_bands = {}  # type: dict
    output_bands = ['red', 'green', 'blue']

    @classmethod
    def fits_raster_bands(cls, available_bands, silent=True, *args, **kwargs):
        if len(available_bands) == 1:
            return True
        if silent:
            return False
        raise KeyError('%s renderer expects one band and got %d bands' % (cls.display_name, len(available_bands)))

    def apply(self, raster, vmin=None, vmax=None):
        self.fits_raster_bands(raster.band_names, silent=False)
        vmin = vmin or min(raster.min())
        vmax = vmax or max(raster.max())
        cmap = plt.get_cmap(self._cmap)
        normalized = np.divide(raster.image.data[0, :, :] - vmin, vmax - vmin)
        image_data = cmap(normalized)
        image_data = image_data[:, :, 0:3]

        # convert floats [0,1] to uint8 [0,255]
        image_data = image_data * 255
        image_data = image_data.astype(self.type)

        image_data = np.rollaxis(image_data, 2)

        # force nodata where it was in original raster:
        mask = _join_masks_from_masked_array(raster.image)
        mask = np.stack([mask[0, :, :]] * 3)
        array = np.ma.array(image_data, mask=mask).filled(0)  # type: np.ndarray
        array = np.ma.array(array, mask=mask)

        return raster.copy_with(image=array, band_names=self.output_bands)


class FirstBandGrayColormapView(ColormapView):
    _cmap = 'gray'
    name = 'fb-cm-gray'
    display_name = "first band gray colormap"
    description = ""

    @classmethod
    def fits_raster_bands(cls, available_bands, silent=True, *args, **kwargs):
        if len(available_bands) > 0:
            return True
        if silent:
            return False
        raise KeyError('%s renderer expects at least one band and got %d bands' % (cls.display_name,
                                                                                   len(available_bands)))


class OneBanders(ProductView):
    """ This family of renderers play with a single band, can be parametrised or not. """

    required_bands = {}  # type: dict
    output_bands = ['gray']

    def apply(self, raster, **kwargs):
        self.fits_raster_bands(raster.band_names, silent=False)
        raster = self._apply(raster)
        raster = raster.astype(np.uint8)
        return raster

    @classmethod
    def fits_raster_bands(cls, available_bands, silent=True, *args, **kwargs):
        if len(available_bands) == 1:
            return True
        if silent:
            return False
        raise KeyError('%s renderer expects one band and got %d bands' % (cls.display_name, len(available_bands)))


class SingleBand(OneBanders):
    name = "SingleBand"
    display_name = "SingleBand"
    description = ""

    def _apply(self, raster):
        return raster


class MagnifyingGlass(OneBanders):
    """ A view for debugging products """
    name = "MagnifyingGlass"
    display_name = "MagnifyingGlass"
    description = ""

    def _apply(self, raster):
        array = (raster.image.data + 1) * 100
        raster = raster.copy_with(image=array)
        return raster


class ProductViewsFactory(BaseFactory):
    __objects = None

    @classmethod
    def objects(cls):
        if not cls.__objects:
            cls.__objects = cls.load_colormaps_subs()
            cls.__objects.update(cls.load_colormaps())
            cls.__objects.update(cls.load_one_banders())
        return cls.__objects

    @classmethod
    def load_colormaps_subs(cls):
        return {p.get_name().lower(): p for p in ColormapView.__subclasses__()}

    @classmethod
    def load_colormaps(cls):
        colormaps = {}
        for colormap in plt.cm.datad.keys():
            name = ("cm-%s" % colormap)
            attr = {
                '_cmap': colormap,
                'name': name,
                'display_name': "colormap %s" % colormap,
                'description': "",
                }
            cm = type(name, (ColormapView,), attr)
            colormaps[name.lower()] = cm
        return colormaps

    @classmethod
    def load_one_banders(cls):
        return {p.get_name().lower(): p for p in OneBanders.__subclasses__()}
