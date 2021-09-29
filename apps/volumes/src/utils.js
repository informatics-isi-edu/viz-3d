import HttpDataAccessHelper from 'vtk.js/Sources/IO/Core/DataAccessHelper/HttpDataAccessHelper';
import macro from 'vtk.js/Sources/macro';
// import { config_params } from './config.js';

export default class image_utils {
    constructor(userParams, config_params) {
	this.userParams = userParams;
	this.query_template = config_params.default_query_template;
	this.skip_headers = userParams['skipHeaders'];
    }
    
    initialize_image(reader) {
	const progressContainer = document.querySelector('.progress');
	const progressCallback = (progressEvent) => {
	    if (progressEvent.lengthComputable) {
		const percent = Math.floor(
		    (100 * progressEvent.loaded) / progressEvent.total
		);
		progressContainer.innerHTML = `Loading ${percent}%`;
	    } else {
		let size = macro.formatBytesToProperUnit(progressEvent.loaded);
		progressContainer.innerHTML = `Loading: ${size}`;
	    }
	};

	return (
	    this.get_options(this.userParams, this.query_template)
		.then ((options) => {
		    this.opts = options;
		    return(HttpDataAccessHelper.fetchBinary(options.File_URL, {progressCallback}));
		})
		.then((data) => {
		    const progressContainer = document.querySelector('.progress');
		    progressContainer.innerHTML = 'Processing ...'
		    progressContainer.style.display = 'block';
		    return(reader.parseAsArrayBuffer(data));
		})
		.then(() => reader.getOutputData())
		.then ((imdata) => {
//		    progressContainer.style.display = 'none';
		    return({
			'image_data': imdata,
			'options': this.opts
		    })
		})
	);
    }

    get_options(userParams, query_template) {
	return new Promise(function(resolve, reject) {    
	    if (userParams['fileURL']) {
		resolve({'File_URL': userParams['fileURL']});
	    } else if (userParams['RID']) {
		let url = window.location.origin + query_template.replace('MY_RID', userParams['RID']);
		console.log(url);
	
		fetch(url)
		    .then ((response) => response.json())
		    .then ((data) => {
			if (data && (data.length == 1)) {
			    resolve(data[0]);
			} else {
			    reject(new Error("couldn't get image metadata"));
			}
		    });
	    } else {
		reject(new Error("must specify either RID or fileURL"));
	    }
	})
    }
    
    add_headers(parent) {
	if (this.skip_headers) {
	    return;
	}
//	let elts = parent.getElementsByClassName("image-metadata");
	let div = document.createElement("div")
	div.setAttribute("class", "image-metadata");	
	parent.appendChild(div);

	let table=document.createElement("table");
	div.appendChild(table);
	let tbody=document.createElement("table");
	table.appendChild(tbody);

	let tr =document.createElement("tr");
	tr.setAttribute("class", "image-metadata-source");
	tr.innerHTML=`<a href="${window.location.origin}/id/${this.opts.RID}">${this.opts.Downsample_Percent}% sample</a> of ${this.opts.Consortium} image <a href="${window.location.origin}/id/${this.opts.Source_Image}">${this.opts.Source_Image}</a>: "${this.opts.Title}"`;
	tbody.appendChild(tr);
	tr =document.createElement("tr");
	tr.setAttribute("class", "image-metadata-pi");
	tr.innerText=`Principal Investigator: ${this.opts.PI_Name}`;
	tbody.appendChild(tr);
    }

    default_style() {
	return({
	    margin: '0',
	    padding: '0',
	    position: 'absolute',
	    top: '50px',
	    left: '0',
	    width: '100%',
	    height: '100%',
	    overflow: 'hidden'
	});
    }

    get_canvas_size() {
	let canvas = document.querySelector("canvas");
	return {
	    "width": canvas.getBoundingClientRect().width,
	    "height": canvas.getBoundingClientRect().height
	}
    }
    
}
