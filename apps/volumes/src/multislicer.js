import 'vtk.js/Sources/favicon';

import vtkFullScreenRenderWindow from 'vtk.js/Sources/Rendering/Misc/FullScreenRenderWindow';
import vtkImageMapper from 'vtk.js/Sources/Rendering/Core/ImageMapper';
import vtkImageSlice from 'vtk.js/Sources/Rendering/Core/ImageSlice';
import msControlPanel from './ms_control_panel.html';
import vtkMapper from 'vtk.js/Sources/Rendering/Core/Mapper';
import vtkActor from 'vtk.js/Sources/Rendering/Core/Actor';
import vtkColorTransferFunction from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction';
import vtkRenderer from 'vtk.js/Sources/Rendering/Core/Renderer';
import vtkOrientationMarkerWidget from 'vtk.js/Sources/Interaction/Widgets/OrientationMarkerWidget';
import vtkVolumeMapper from 'vtk.js/Sources/Rendering/Core/VolumeMapper';
import vtkVolume from 'vtk.js/Sources/Rendering/Core/Volume';
import vtkPiecewiseFunction from 'vtk.js/Sources/Common/DataModel/PiecewiseFunction';
import vtkColorMaps from 'vtk.js/Sources/Rendering/Core/ColorTransferFunction/ColorMaps';
import vtkBoundingBox from 'vtk.js/Sources/Common/DataModel/BoundingBox';
import vtkLabelWidget from 'vtk.js/Sources/Interaction/Widgets/LabelWidget';
import TextAlign from 'vtk.js/Sources/Interaction/Widgets/LabelRepresentation/Constants';


// import { VtkDataTypes } from 'vtk.js/Sources/Common/Core/DataArray/Constants';


export default class multislicer {
    constructor(image_data, container, utils) {
	global.ms = this;
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
	const control_panel_style = {
	    position: 'static',
	    left: '25px',
	    top: '25px',
	    backgroundColor: 'white',
	    borderRadius: '5px',
	    listStyle: 'none',
	    padding: '5px 10px',
	    margin: '0',
	    display: 'block',
	    border: 'solid 1px black',
	    maxWidth: 'calc(100% - 70px)',
	    maxHeight: 'calc(100% - 60px)',
	    overflow: 'auto',
	};
	
	this.fullScreenRenderWindow.resize();
	this.renderWindow = this.fullScreenRenderWindow.getRenderWindow();
	this.renderer = vtkRenderer.newInstance({preserveColorBuffer: true});
	this.renderWindow.addRenderer(this.renderer);
	this.dimensions = ["I", "J", "K"];
	this.imageActorMappers = {};
	global.imageActorMappers = this.imageActorMappers;

	const dataRange = this.image_data.getPointData().getScalars().getRange();
	this.fullScreenRenderWindow.addController(msControlPanel,
						  {controlPanelStyle: control_panel_style}
						 );
	let msc = this.fullScreenRenderWindow.getControlContainer();
	msc.setAttribute("class", "controller-envelope");
	msc.setAttribute("id", "multislice-envelope");
	msc.style.position = null;


	this.renderer.setViewport([0, 0, 1, 1]);	
	const filters = ["base", "flat"];
	this.dimensions.forEach(dim => {
	    this.imageActorMappers[dim] = {
		"sliceClass" : ".slice" + dim
	    };
	    this.imageActorMappers[dim]["base"] = {"mapper": vtkImageMapper.newInstance(),
						   "actor": vtkImageSlice.newInstance()};
	    this.imageActorMappers[dim]["flat"] = {"mapper": vtkImageMapper.newInstance(),
						   "actor": vtkImageSlice.newInstance(),
						   "renderer": vtkRenderer.newInstance({preserveColorBuffer: true})};
	    
	    this.imageActorMappers[dim].base.actor.getProperty().setIndependentComponents(true);
	    this.imageActorMappers[dim].flat.actor.getProperty().setIndependentComponents(true);
	    this.imageActorMappers[dim].flat.renderer.setInteractive(false);
	    let am = this.imageActorMappers[dim].base;
	    this.renderer.addActor(am.actor);
	    am.actor.setMapper(am.mapper);

	    this.imageActorMappers[dim].flat.renderer.addActor(this.imageActorMappers[dim].flat.actor);
	    this.imageActorMappers[dim].flat.actor.setMapper(this.imageActorMappers[dim].flat.mapper);
	    this.imageActorMappers[dim].base.mapper.setInputData(this.image_data);
	    this.imageActorMappers[dim].flat.mapper.setInputData(this.image_data);
	    this.imageActorMappers[dim].flat.renderer.setPreserveColorBuffer(false);
	    this.imageActorMappers[dim].flat.renderer.setBackground(.945, .945, .945);
	    this.renderWindow.addRenderer(this.imageActorMappers[dim].flat.renderer);
	});
	this.set_viewport_coords(null, null);	
	this.imageActorMappers["I"]["slicefunc"] = (num) => {
	    filters.forEach(key => {
		this.imageActorMappers["I"][key].mapper.setISlice(num);
	    });
	}
	this.imageActorMappers.I.flat.actor.rotateY(270);
	this.imageActorMappers.I.flat.actor.rotateX(90);	
	
	this.imageActorMappers["J"]["slicefunc"] = (num) => {
	    filters.forEach(key => {
		this.imageActorMappers["J"][key].mapper.setJSlice(num);
	    });
	};
	this.imageActorMappers.J.flat.actor.rotateX(90);
	
	this.imageActorMappers["K"]["slicefunc"] = (num) => {
	    filters.forEach(key => {
		this.imageActorMappers["K"][key].mapper.setKSlice(num);
	    });
	};
	this.dimensions.forEach(axis => {
	    this.imageActorMappers[axis].slicefunc(30);
	});

	this.dimensions.forEach((dim, idx) => {
	    let sliceClass = this.imageActorMappers[dim].sliceClass;	    
	    //	    ["base", "points"].forEach(key => {
	    const el = document.querySelector(sliceClass);
	    let extent = this.image_data.getExtent();
	    el.setAttribute('min', extent[idx * 2 + 0]);
	    el.setAttribute('max', extent[idx * 2 + 1]);
	    el.setAttribute('value', 30);
	    document.querySelector(sliceClass).addEventListener('input', (e) => {
		this.imageActorMappers[dim].slicefunc(Number(e.target.value));
		this.renderWindow.render();
	    });
	});
	['.colorLevel', '.colorWindow'].forEach((selector) => {
	    document.querySelector(selector).setAttribute('max', dataRange[1]);
	    document.querySelector(selector).setAttribute('value', dataRange[1]);
	});
	document
	    .querySelector('.colorLevel')
	    .setAttribute('value', (dataRange[0] + dataRange[1]) / 2);
	this.updateColorLevel();
	this.updateColorWindow()

	document
	    .querySelector('.colorLevel')
	    .addEventListener('input', (e) => this.updateColorLevel(e));
	document
	    .querySelector('.colorWindow')
	    .addEventListener('input', (e) => this.updateColorWindow(e));
//	this.addOrientationWidget();
	this.fullScreenRenderWindow.setResizeCallback(({ width, height }) => {
	    this.set_viewport_coords(width, height);
	});
	this.utils.add_headers(this.container);
    }    

    show() {
	this.container.style.display = 'inline';	
	this.renderer.resetCamera();
	this.dimensions.forEach(dim => {
	    this.imageActorMappers[dim].flat.renderer.resetCamera();
	});
	this.fullScreenRenderWindow.resize();
	this.renderer.resetCameraClippingRange();	
	this.renderWindow.render();
    }
    
    updateColorLevel(e) {
	const colorLevel = Number(
	    (e ? e.target : document.querySelector('.colorLevel')).value
	);
	this.dimensions.forEach(dim => {
	    this.imageActorMappers[dim].base.actor.getProperty().setColorLevel(colorLevel);
	    this.imageActorMappers[dim].flat.actor.getProperty().setColorLevel(colorLevel);	    
	});
	this.renderWindow.render();
    }

    updateColorWindow(e) {
	const colorLevel = Number(
	    (e ? e.target : document.querySelector('.colorWindow')).value
	);
	this.dimensions.forEach(dim => {
	    this.imageActorMappers[dim].base.actor.getProperty().setColorWindow(colorLevel);
	    this.imageActorMappers[dim].flat.actor.getProperty().setColorWindow(colorLevel);	    
	});
	this.renderWindow.render();
    }

    hide() {
	this.container.style.display = 'none';	
    }
    addOrientationWidget() {
	this.axes = vtkVolume.newInstance();
	const mapper = vtkVolumeMapper.newInstance();
	this.axes.setMapper(mapper);
	mapper.setInputData(this.image_data);
	this.set_colors_and_shading(this.axes, mapper, 'erdc_rainbow_bright', this.image_data);
	const orientationWidget = vtkOrientationMarkerWidget.newInstance({
	    actor: this.axes,
	    interactor: this.renderWindow.getInteractor(),
	});
	orientationWidget.setEnabled(true);
	orientationWidget.setViewportCorner(
	    vtkOrientationMarkerWidget.Corners.TOP_RIGHT
	);
	orientationWidget.setViewportSize(1.0);
//	orientationWidget.setMinPixelSize(300);
//	orientationWidget.setMaxPixelSize(600);
    }

    set_colors_and_shading(actor, mapper, preset_name, image_data) {
	const piecewiseFun = vtkPiecewiseFunction.newInstance();
	const dataArray =
              image_data.getPointData().getScalars() || image_data.getPointData.getArrays()[0];
	const dataRange = dataArray.getRange();	

	let step = (dataRange[1] - dataRange[0])/8;
	for(let i = 0; i <= 8; i++) {
	    piecewiseFun.addPoint(i * step, i/8);
	}
	actor.getProperty().setScalarOpacity(0, piecewiseFun);
 	actor.getProperty().setInterpolationTypeToLinear();
	actor.getProperty().setScalarOpacityUnitDistance(
            0,
            vtkBoundingBox.getDiagonalLength(image_data.getBounds()) /
		Math.max(...image_data.getDimensions())
	);
	actor.getProperty().setGradientOpacityMinimumValue(0, 0);
	actor.getProperty().setGradientOpacityMaximumValue(0, (dataRange[1] - dataRange[0]));
	actor.getProperty().setShade(true);
	actor.getProperty().setUseGradientOpacity(0, true);
	actor.getProperty().setGradientOpacityMinimumOpacity(0, 0.0);
	actor.getProperty().setGradientOpacityMaximumOpacity(0, 1.0);
	actor.getProperty().setAmbient(0.2);
	actor.getProperty().setDiffuse(0.7);
	actor.getProperty().setSpecular(0.3);
	actor.getProperty().setSpecularPower(8.0);

       // set this as small as possible without exceeding maximum samples per ray
       // this may be off a little because it's not taking rotation into account,
       // but it should be pretty close.

       mapper.setSampleDistance(
           Math.ceil(
               100 *
                   (vtkBoundingBox.getDiagonalLength(image_data.getBounds()) / mapper.getMaximumSamplesPerRay())
                   / 100));	

	const lookupTable = vtkColorTransferFunction.newInstance();
	lookupTable.applyColorMap(vtkColorMaps.getPresetByName(preset_name));
	lookupTable.setMappingRange(...dataRange);
	lookupTable.updateRange();
	actor.getProperty().setRGBTransferFunction(0, lookupTable);

    }

    addLabels() {
	this.dimensions.forEach(dim => {
	    let widget = vtkLabelWidget.newInstance();
	    widget.setInteractor(this.renderWindow.getInteractor());
	    widget.setEnabled(1);
	    widget.getWidgetRep().setLabelText(dim);
	    widget.getWidgetRep().setLabelStyle({
		fontSize: 12,
		fontColor: 'red',
		strokeColor: 'black'
	    });
	    widget.getWidgetRep().setTextAlign('RIGHT');
	    widget.getWidgetRep().setVerticalAlign('TOP');	    	    
	    this.imageActorMappers[dim]["label"] = widget;
	});
	this.setLabelPositions();
    }

    setLabelPositions() {
	this.dimensions.forEach(dim => {
	    this.imageActorMappers[dim].label.getWidgetRep().setDisplayPosition([
		this.viewport_coords[dim][2] * this.utils.get_canvas_size().width,
		this.viewport_coords[dim][3] * this.utils.get_canvas_size().height,
		0
	    ]);
	});
    }

    set_viewport_coords(viewportWidth, viewportHeight) {
	if (! viewportWidth || ! viewportHeight) {
	    let canvas_size = this.utils.get_canvas_size();
	    viewportWidth = canvas_size.width;
	    viewportHeight = canvas_size.height;
	}
	let controllerElement = document.querySelector('.controller-widget');
	let controllerWidth = controllerElement.getBoundingClientRect().right;
	let controllerHeight = controllerElement.getBoundingClientRect().height;
	let controllerTop = controllerElement.getBoundingClientRect().top;

	let boxWidth = controllerWidth / viewportWidth;
	let boxHeight = (viewportHeight - controllerHeight)/ (viewportHeight * 3);
	let offset = .005;
	    
	this.viewport_coords = {
	    "volume": [boxWidth, 0, 1, 1],
	    "I": [0, offset/2 + 2 * boxHeight, boxWidth, 3 * boxHeight - offset/2],
	    "J": [0, offset/2 + boxHeight, boxWidth, 2 * boxHeight - offset/2],
	    "K": [0, offset/2, boxWidth, boxHeight - offset/2]
	};
	this.renderer.setViewport([0, 0, 1, 1]);
	this.dimensions.forEach(dim => {
	    this.imageActorMappers[dim].flat.renderer.setViewport(this.viewport_coords[dim]);
	});
    }
}
