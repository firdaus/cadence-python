var fs = require('fs');

let thriftParser = require('./thrift-parser');
file = process.argv[2]
var contents = fs.readFileSync(file, 'utf8');
contents = contents.replace(new RegExp("\\(js.type = \"Long\"\\)", 'g'), "")
contents = contents.replace(new RegExp("\\(js.type = \'Long\'\\)", 'g'), "")
let ast = thriftParser(contents) 
console.log(JSON.stringify(ast, null, 2))

