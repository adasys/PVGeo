__all__ = [
    'refoldidx',
    'tableToGrid',
]

import vtk
from vtk.util import numpy_support as nps
import numpy as np

#---- Table To Grid Stuff ----#

def _unpack(arr, extent, order='C'):
    """
    This is a helper method that handles the initial unpacking of a data array.
    ParaView and VTK use Fortran packing so this is convert data saved in
    C packing to Fortran packing.
    """
    n1,n2,n3 = extent[0],extent[1],extent[2]
    if order == 'C':
        arr = np.reshape(arr, (n1,n2,n3))
        arr = np.swapaxes(arr,0,2)
        extent = np.shape(arr)
    elif order == 'F':
        # effectively doing nothing
        #arr = np.reshape(arr, (n3,n2,n1))
        return arr.flatten(), extent
    return arr.flatten(), extent


def _rearangeSEPlib(arr, extent):
    """
    This is a helper method to swap axes   when using SEPlib axial conventions.
    """
    n1,n2,n3 = extent[0],extent[1],extent[2]
    arr = np.reshape(arr, (n3,n2,n1))
    arr = np.swapaxes(arr,0,2)
    return arr.flatten(), (n1,n2,n3)

def _transposeXY(arr, extent, SEPlib=False):
    """
    Transposes X and Y axes. Needed by Whitney's research group for PoroTomo.
    """
    n1,n2,n3 = extent[0],extent[1],extent[2]
    arr = np.reshape(arr, (n1,n2,n3))
    if SEPlib:
        arr = np.swapaxes(arr,1,2)
        ext = (n1,n3,n2)
    else:
        print('bef: ', np.shape(arr))
        arr = np.swapaxes(arr,0,1)
        print('aft: ', np.shape(arr))
        ext = np.shape(arr)
    return arr.flatten(), ext


def _refold(arr, extent, SEPlib=True, order='F', swapXY=False):
    """
    This is a helper method to handle grabbing a data array and make sure it is
    ready for VTK/Fortran ordering in vtkImageData.
    """
    # Fold into 3D using extents. Packing dimensions should be in order extent
    arr, extent = _unpack(arr, extent, order=order)
    if SEPlib:
        arr, extent = _rearangeSEPlib(arr, extent)
    if swapXY:
        arr, extent = _transposeXY(arr, extent, SEPlib=SEPlib)
    return arr, extent

def refoldidx(SEPlib=True, swapXY=False):
    """
    Theses are indexing corrections to set the spacings and origin witht the correct axes after refolding.
    """
    if SEPlib:
        idx = (2,1,0)
        if swapXY:
            idx = (1,2,0)
    else:
        idx = (0,1,2)
        if swapXY:
            idx = (1,0,2)
    return idx

def tableToGrid(pdi, extent, spacing=(1,1,1), origin=(0,0,0), SEPlib=True, order='F', swapXY=False, pdo=None):
    """
    Converts a table of data arrays to vtkImageData given an extent to reshape that table.
    Each column in the table will be treated as seperate data arrays for the described data space
    """
    cols = pdi.GetNumberOfColumns()
    rows = pdi.GetColumn(0).GetNumberOfTuples()

    # Output Data Type:
    if pdo is None:
        pdo = vtk.vtkImageData()

    idx = refoldidx(SEPlib=SEPlib, swapXY=swapXY)
    nx,ny,nz = extent[idx[0]],extent[idx[1]],extent[idx[2]]
    sx,sy,sz = spacing[idx[0]],spacing[idx[1]],spacing[idx[2]]
    ox,oy,oz = origin[idx[0]],origin[idx[1]],origin[idx[2]]
    # make sure dimensions work
    if (nx*ny*nz != rows):
        raise Exception('Total number of elements must remain %d. Check reshape dimensions (n1 by n2 by n3).' % (rows))

    pdo.SetDimensions(nx, ny, nz)
    pdo.SetOrigin(ox, oy, oz)
    pdo.SetSpacing(sx, sy, sz)
    pdo.SetExtent(0,nx-1, 0,ny-1, 0,nz-1)

    # Add all columns of the table as arrays to the PointData
    for i in range(cols):
        c = pdi.GetColumn(i)
        name = c.GetName()
        arr = nps.vtk_to_numpy(c)
        arr, ext = _refold(arr, extent, SEPlib=SEPlib, order=order, swapXY=swapXY)
        c = nps.numpy_to_vtk(num_array=arr,deep=True)
        c.SetName(name)
        #pdo.GetCellData().AddArray(c) # Should we add here? flipper won't flip these...
        pdo.GetPointData().AddArray(c)
        scal = pdo.GetPointData().GetArray(i)

    return pdo