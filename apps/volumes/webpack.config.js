const path = require('path');

const vtkRules = require('vtk.js/Utilities/config/dependency.js').webpack.core.rules;
const cssRules = require('vtk.js/Utilities/config/dependency.js').webpack.css.rules;


module.exports = {
    entry: {
	app: path.join(__dirname, 'src', 'main.js'),
    },
    output: {
	path: path.join(__dirname, 'dist'),
	filename: '[name].js',
	hashFunction: 'xxhash64',
    },
    mode: 'development',
    module: {
	rules: [
	    {
		test: /\.js$/,
		loader: 'babel-loader',
		exclude: /node-modules/,
	    },
	    {
		test: /\.css$/,
		loader: 'css-loader',
		exclude: /node-modules/,
	    },
	    { test: /\.html$/, loader: 'html-loader' },
            { test: /\.(png|jpg)$/, use: 'url-loader?limit=81920' },
            { test: /\.svg$/, use: [{ loader: 'raw-loader' }] },
	].concat(vtkRules),
    },
    devtool: 'inline-source-map',
    resolve: {
	extensions: ['.js'],
    },
    devServer: {
	contentBase: path.join(__dirname, 'dist'),
	disableHostCheck: true,
	hot: false,
	quiet: false,
	noInfo: false,
	stats: {
	    colors: true,
	},
    },
};
