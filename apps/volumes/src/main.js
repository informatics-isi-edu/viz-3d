import 'vtk.js/Sources/favicon';

import vtkURLExtract from 'vtk.js/Sources/Common/Core/URLExtract';
import vtkXMLImageDataReader from 'vtk.js/Sources/IO/XML/XMLImageDataReader';
import multislicer from './multislicer.js';
import volume from './volume.js';
import image_utils from "./utils.js";

const userParams = vtkURLExtract.extractURLParameters();
const utils = new image_utils(userParams);
const fileURL = userParams['fileURL'];
const skipHeaders = userParams['skipHeaders'];

const reader = vtkXMLImageDataReader.newInstance();

let current_url = null;

const viewers = {};

const iOS = /iPad|iPhone|iPod/.test(window.navigator.platform);

if (iOS) {
  document.querySelector('body').classList.add('is-ios-device');
}

function dispatch(args) {
    viewers['multislice'] = {'obj': new multislicer(args.image_data, document.querySelector('.multislice'), utils)};    
    viewers['volume'] = {'obj': new volume(args.image_data, document.querySelector('.volume'), utils)};
    let buttons=document.querySelectorAll('.tablinks');
    let first = 1;	
    buttons.forEach(b => {
	let key = b.getAttribute('id');
	viewers[key]['button'] = b;
	if ( first) {
	    viewers[key].obj.show();
	} else {
	    viewers[key].obj.hide();
	}
	first = 0;
    });
    
    let tabs = document.querySelectorAll('.tablinks');
    tabs.forEach(tab => {
	tab.addEventListener('click', (event) => changeEvent(event));
    });
}	       

export function changeListener(action) {
    for (let v in viewers) {
	let viewer = viewers[v].obj;
	if (v != action) {
	    viewers[v].button.blur();
	    viewer.hide();
	}
    }
    viewers[action].button.focus();
    viewers[action].obj.show();
}

function changeEvent(event) {
    changeListener(event.target.id);
}


export function show(action) {
    viewers[action].obj.show();
}

utils.initialize_image(reader)
    .then((args) => dispatch(args));

global.viewers = viewers;
global.skipHeaders = skipHeaders;
