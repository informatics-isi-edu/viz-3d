import vtkFullScreenRenderWindow from 'vtk.js/Sources/Rendering/Misc/FullScreenRenderWindow';
import vtkVolume from 'vtk.js/Sources/Rendering/Core/Volume';
import vtkVolumeMapper from 'vtk.js/Sources/Rendering/Core/VolumeMapper';
import vtkPiecewiseFunction from 'vtk.js/Sources/Common/DataModel/PiecewiseFunction';
import vtkColorTransferFunction from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction';
import vtkColorMaps from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction/ColorMaps';
import vtkBoundingBox from 'vtk.js/Sources/Common/DataModel/BoundingBox';
import vtkPiecewiseGaussianWidget from 'vtk.js/Sources/Interaction/Widgets/PiecewiseGaussianWidget';
import vtkVolumeController from 'vtk.js/Sources/Interaction/UI/VolumeController';
import vtkFPSMonitor from 'vtk.js/Sources/Interaction/UI/FPSMonitor';

import macro from 'vtk.js/Sources/macro';
import style from './VolumeViewer.module.css';

export default class volume {
    constructor(image_data, container, utils) {
	this.image_data = image_data;
	this.container = container;
	this.utils = utils;
	this.fullScreenRenderWindow = vtkFullScreenRenderWindow.newInstance(
	    {rootContainer : this.container,
	      containerStyle: this.utils.default_style()
	    });
	this.setup();
    }

    setup() {
	this.utils.add_headers(this.container);
	this.renderer = this.fullScreenRenderWindow.getRenderer();
	this.renderWindow = this.fullScreenRenderWindow.getRenderWindow();

	this.actor = vtkVolume.newInstance();
	this.mapper = vtkVolumeMapper.newInstance();
	this.actor.setMapper(this.mapper);
	this.mapper.setInputData(this.image_data);
	

	const dataArray =
              this.image_data.getPointData().getScalars() || this.image_data.getPointData.getArrays()[0];
	const dataRange = dataArray.getRange();

	const lookupTable = vtkColorTransferFunction.newInstance();
	global.lookupTable = lookupTable;
	this.piecewiseFun = vtkPiecewiseFunction.newInstance();
	lookupTable.applyColorMap(vtkColorMaps.getPresetByName('erdc_rainbow_bright'));
	global.getPreset = vtkColorMaps.getPresetByName;

	this.actor.getProperty().setRGBTransferFunction(0, lookupTable);

	this.actor.getProperty().setScalarOpacity(0, this.piecewiseFun);

	global.range = dataRange;
	lookupTable.setMappingRange(dataRange[0], dataRange[1]);
	lookupTable.updateRange();
	const sampleDistance =
              0.7 *
              Math.sqrt(
		  this.image_data
                      .getSpacing()
                      .map((v) => v * v)
                      .reduce((a, b) => a+b, 0)
              );
	this.mapper.setSampleDistance(sampleDistance);

 	this.actor.getProperty().setInterpolationTypeToLinear();	

	this.actor.getProperty().setScalarOpacityUnitDistance(
            0,
            vtkBoundingBox.getDiagonalLength(this.image_data.getBounds()) /
		Math.max(...this.image_data.getDimensions())
	);

	this.actor.getProperty().setGradientOpacityMinimumValue(0, 0);
	this.actor.getProperty().setGradientOpacityMaximumValue(0, (dataRange[1] - dataRange[0]) * 0.05);
	this.actor.getProperty().setShade(true);
	this.actor.getProperty().setUseGradientOpacity(0, true);
	this.actor.getProperty().setGradientOpacityMinimumOpacity(0, 0.0);
	this.actor.getProperty().setGradientOpacityMaximumOpacity(0, 1.0);
	this.actor.getProperty().setAmbient(0.2);
	this.actor.getProperty().setDiffuse(0.7);
	this.actor.getProperty().setSpecular(0.3);
	this.actor.getProperty().setSpecularPower(8.0);
	this.renderer.addVolume(this.actor);

	this.setup_widget();
    }

    show() {
	if (this.image_data.getPointData().getNumberOfComponents() === 2) {
	    this.actor.getProperty().setIndependentComponents(true);
	    this.actor.getProperty().setComponentWeight(1, 0);
	}
	this.container.style.display = 'inline';
	this.fullScreenRenderWindow.resize();
	this.renderer.resetCamera();
	this.renderer.resetCameraClippingRange();	
	this.renderWindow.render();
    }

    hide() {
	this.container.style.display = 'none';
    }

    setup_widget() {
	this.controllerWidget = vtkVolumeController.newInstance({
	    size: [400, 150],
	    rescaleColorMap: true
	});

	this.envelope = document.createElement('div');
	this.envelope.setAttribute("class", "controller-envelope");
	this.envelope.setAttribute("id", "volume-controller");
	this.container.appendChild(this.envelope);

	const widgetContainer = document.createElement('details');
//	widgetContainer.setAttribute("open", "");
	this.envelope.appendChild(widgetContainer);
	const widgetSummary = document.createElement('summary');
	widgetSummary.textContent = "Appearance Controls";
	widgetContainer.appendChild(widgetSummary);
	
	this.controllerWidget.setContainer(widgetContainer);
	this.controllerWidget.setupContent(this.renderWindow, this.actor, true);
	this.fpsMonitor = vtkFPSMonitor.newInstance();

	this.fullScreenRenderWindow.setResizeCallback(({ width, height }) => {
	    // 2px padding + 2x1px boder + 5px edge = 14
	    if (width === 0) {
		return;
	    }
	    if (width > 414) {
		this.controllerWidget.setSize(400, 150);
	    } else {
		this.controllerWidget.setSize(width - 14, 150);
	    }
	    this.controllerWidget.render();
	    this.fpsMonitor.update();
	});
    }

    setup_piecewise_widget() {
	const widgetHeader = document.createElement('summary');
	widgetHeader.textContent = "Color and Opacity";
	this.envelope.appendChild(widgetHeader);
	const widgetContainer = document.createElement('details');
	widgetContainer.addAttribute("class", "controller-widget");
	widgetContainer.addAttribute("id", "piecewise-gaussian");
	widgetHeader.appendChild(widgetContainer);

	const widget = vtkPiecewiseGaussianWidget.newInstance({
	    numberOfBins: 256,
	    size: [400, 150],
	});

	widget.updateStyle({
	    backgroundColor: 'rgba(255, 255, 255, 0.6)',
	    histogramColor: 'rgba(100, 100, 100, 0.5)',
	    strokeColor: 'rgb(0, 0, 0)',
	    activeColor: 'rgb(255, 255, 255)',
	    handleColor: 'rgb(50, 150, 50)',
	    buttonDisableFillColor: 'rgba(255, 255, 255, 0.5)',
	    buttonDisableStrokeColor: 'rgba(0, 0, 0, 0.5)',
	    buttonStrokeColor: 'rgba(0, 0, 0, 1)',
	    buttonFillColor: 'rgba(255, 255, 255, 1)',
	    strokeWidth: 2,
	    activeStrokeWidth: 3,
	    buttonStrokeWidth: 1.5,
	    handleWidth: 3,
	    iconSize: 20, // Can be 0 if you want to remove buttons (dblClick for (+) / rightClick for (-))
	    padding: 10,
	});
	
	widget.setDataArray(this.image_data.getPointData().getScalars());

	widget.addGaussian(0.425, 0.5, 0.2, 0.3, 0.2);
	widget.addGaussian(0.75, 1, 0.3, 0, 0);
	widget.applyOpacity(this.piecewiseFun);
	widget.setContainer(widgetContainer);

	widget.bindMouseListeners();
	widget.onOpacityChange(() => {
	    widget.applyOpacity(this.piecewiseFun);
	    this.renderWindow.render();
	});
    }
}
