from numpy import arctan2, sqrt, pi, abs, dstack, clip, transpose, inf, \
    random, zeros, ones, asarray, corrcoef, allclose, maximum, add, multiply


class Colorize(object):
    """
    Class for turning numerical data into colors.

    Supports a set of custom conversions (rgb, hsv, polar, and indexed)
    as well as conversions to standard matplotlib colormaps through
    either a passed colormap or a string specification.

    If vmax and vmin are not specified, numerical data will be automatically
    scaled by its maximum and minimum values.

    Supports two-dimensional and three-dimensional data.
    
    Attributes
    ----------
    cmap : string, optional, default = rainbow
        The colormap to convert to, can be one of a special set of conversions
        (rgb, hsv, polar, indexed), a matplotlib colormap object, or a string
        specification of a matplotlib colormap

    scale : float, optional, default = 1
        How to scale amplitude during color conversion, controls brighthness

    colors : list, optional, default = None
        List of colors for 'indexed' option

    vmin : scalar, optional, default = None
        Numerical value to set to 0 during normalization, values below will be clipped

    vmax : scalar, optional, default = None
        Numerical value to set to 1 during normalization, values above will be clipped.
    """

    def __init__(self, cmap='rainbow', scale=1, colors=None, vmin=None, vmax=None):
        self.cmap = cmap
        self.scale = scale
        self.colors = colors
        self.vmin = vmin
        self.vmax = vmax

    def transform(self, img, mask=None, background=None):
        """
        Colorize numerical image data.

        Input can either be a single array or a list of arrays.
        Depending on the colorization option, each array must either be
        2 or 3 dimensional, see parameters.

        Parameters
        ----------
        img : array
            The image(s) to colorize. For rgb, hsv, polar, and indexed conversions,
            must be of shape (c, x, y, z) or (c, x, y), where c is the dimension
            containing the information for colorizing. For colormap conversions,
            must be of shape (x, y, z) or (x, y).

        mask : array
            An additional image to mask the luminance channel of the first one.
            Must be of shape (x, y, z) or (x, y), and must match dimensions of images.
            Must be strictly positive (and will be clipped below at 0).

        background : array
            An additional image to display as a grayscale background.
            Must be of shape (x, y, z) or (x, y), and must match dimensions of images.

        Returns
        -------
        Arrays with RGB values, with shape (x, y, z, 3) or (x, y, 3)
        """

        from matplotlib.cm import get_cmap
        from matplotlib.colors import ListedColormap, LinearSegmentedColormap, hsv_to_rgb, Normalize

        img = asarray(img)
        dims = img.shape
        self._checkDims(dims)

        norm = Normalize(vmin=self.vmin, vmax=self.vmax, clip=True)
        img = norm(img)

        if mask is not None:
            mask = self._prepareMask(mask)
            self._checkMixedDims(mask.shape, dims)

        if background is not None:
            background = self._prepareMask(background)
            self._checkMixedDims(background.shape, dims)

        if self.cmap == 'rgb':
            if img.ndim == 4:
                out = transpose(img, [1, 2, 3, 0])
            if img.ndim == 3:
                out = transpose(img, [1, 2, 0])

        elif self.cmap == 'hsv':
            if img.ndim == 4:
                out = zeros((dims[1], dims[2], dims[3], 3))
                for i in range(0, dims[3]):
                    out[:, :, i, :] = hsv_to_rgb(dstack((img[0][:, :, i], img[1][:, :, i], img[2][:, :, i])))
            if img.ndim == 3:
                out = hsv_to_rgb(dstack((img[0], img[1], img[2])))

        elif self.cmap == 'polar':
            theta = ((arctan2(-img[0], -img[1]) + pi/2) % (pi*2)) / (2 * pi)
            rho = sqrt(img[0]**2 + img[1]**2)
            if img.ndim == 4:
                saturation = ones((dims[1], dims[2]))
                out = zeros((dims[1], dims[2], dims[3], 3))
                for i in range(0, dims[3]):
                    out[:, :, i, :] = hsv_to_rgb(dstack((theta[:, :, i], saturation, self.scale*rho[:, :, i])))
            if img.ndim == 3:
                saturation = ones((dims[1], dims[2]))
                out = hsv_to_rgb(dstack((theta, saturation, self.scale*rho)))

        elif self.cmap == 'indexed':
            if img.ndim == 4:
                out = zeros((dims[1], dims[2], dims[3], 3))
            if img.ndim == 3:
                out = zeros((dims[1], dims[2], 3))
            for ix, clr in enumerate(self.colors):
                cmap = LinearSegmentedColormap.from_list('blend', [[0, 0, 0], clr])
                tmp = cmap(img[ix])
                if img.ndim == 4:
                    tmp = tmp[:, :, :, 0:3]
                if img.ndim == 3:
                    tmp = tmp[:, :, 0:3]
                out = maximum(out, clip(tmp, 0, 1))

        elif isinstance(self.cmap, ListedColormap):
            if img.ndim == 3:
                out = self.cmap(img)
                out = out[:, :, :, 0:3]
            if img.ndim == 2:
                out = self.cmap(img)
                out = out[:, :, 0:3]

        elif isinstance(self.cmap, str):
            func = lambda x: get_cmap(self.cmap, 256)(x)
            out = func(img)
            if img.ndim == 3:
                out = out[:, :, :, 0:3]
            if img.ndim == 2:
                out = out[:, :, 0:3]

        else:
            raise Exception('Colorization method not understood')

        out = clip(out * self.scale, 0, 1)

        if mask is not None:
            out = self.blend(out, mask, multiply)

        if background is not None:
            out = self.blend(out, background, add)

        return clip(out, 0, 1)

    @staticmethod
    def blend(img, mask, op=add):

        if mask.ndim == 3:
            for i in range(0, 3):
                img[:, :, :, i] = op(img[:, :, :, i], mask)
        else:
            for i in range(0, 3):
                img[:, :, i] = op(img[:, :, i], mask)

        return img

    def _checkDims(self, dims):

        from matplotlib.colors import ListedColormap

        if self.cmap in ['rgb', 'hsv', 'polar', 'indexed']:
            if self.cmap in ['rgb', 'hsv']:
                if dims[0] != 3:
                    raise Exception('First dimension must be 3 for %s conversion' % self.cmap)
            if self.cmap in ['polar']:
                if dims[0] != 2:
                    raise Exception('First dimension must be 2 for %s conversion' % self.cmap)
            if self.cmap in ['indexed']:
                if dims[0] != len(self.colors):
                    raise Exception('First dimension must be %g for %s conversion with list %s'
                                    % (len(self.colors), self.cmap, self.colors))

        elif isinstance(self.cmap, ListedColormap) or isinstance(self.cmap, str):
            if len(dims) not in [2, 3]:
                raise Exception('Number of dimensions must be 2 or 3 for %s conversion' % self.cmap)

    def _checkMixedDims(self, dims1, dims2):

        from matplotlib.colors import ListedColormap

        if self.cmap in ['rgb', 'hsv', 'polar', 'indexed']:
            if not allclose(dims1, dims2[1:]):
                raise Exception

        elif isinstance(self.cmap, ListedColormap) or isinstance(self.cmap, str):
            if not allclose(dims1, dims2):
                raise Exception

    @staticmethod
    def _prepareMask(mask):

        mask = asarray(mask)
        mask = clip(mask, 0, inf)

        return mask

    @staticmethod
    def _prepareBackground(background):

        from matplotlib.colors import Normalize

        background = asarray(background)
        background = Normalize()(background)

        return background


    @classmethod
    def optimize(cls, mat, asCmap=False):
        """
        Optimal colors based on array data similarity.

        Given an (n, m) data array with n m-dimensional data points,
        tries to find an optimal set of n colors such that the similarity
        between colors in 3-dimensional space is well-matched to the similarity
        between the data points in m-dimensional space.

        Parameters
        ----------
        mat : array-like
            Array of data points to use for estimating similarity.

        asCmap : boolean, optional, default = False
            Whether to return a matplotlib colormap, if False will
            return a list of colors.
        """

        mat = asarray(mat)

        if mat.ndim < 2:
            raise Exception('Input array must be two-dimensional')

        nclrs = mat.shape[0]

        from scipy.spatial.distance import pdist, squareform
        from scipy.optimize import minimize

        distMat = squareform(pdist(mat, metric='cosine')).flatten()

        optFunc = lambda x: 1 - corrcoef(distMat, squareform(pdist(x.reshape(nclrs, 3), 'cosine')).flatten())[0, 1]
        init = random.rand(nclrs*3)
        bounds = [(0, 1) for _ in range(0, nclrs * 3)]
        res = minimize(optFunc, init, bounds=bounds, method='L-BFGS-B')
        newClrs = res.x.reshape(nclrs, 3).tolist()

        from matplotlib.colors import ListedColormap

        if asCmap:
            newClrs = ListedColormap(newClrs, name='from_list')

        return newClrs