class ThriftFileParsingError extends SyntaxError {
  constructor({ message, context, line }) {
    super(message);
    this.context = context;
    this.line = line;
    this.name = 'THRIFT_FILE_PARSING_ERROR';
  }
}

module.exports = (source, offset = 0) => {

  source += '';

  let nCount = 0;
  let rCount = 0;

  let stack = [];

  const record = char => {
    if (char === '\r') rCount++;
    else if (char === '\n') nCount++;
  };
  const save = () => stack.push({ offset, nCount, rCount });
  const restore = () => ({ offset, nCount, rCount } = stack[stack.length - 1]);
  const drop = () => stack.pop();

  const readAnyOne = (...args) => {
    save();
    for (let i = 0; i < args.length; i++) {
      try {
        let result = args[i]();
        drop();
        return result;
      } catch (ignore) {
        restore();
        continue;
      }
    }
    drop();
    throw 'Unexcepted Token';
  };

  const readUntilThrow = (transaction, key) => {
    let receiver = key ? {} : [];
    for (;;) {
      try {
        save();
        let result = transaction();
        key ? receiver[result[key]] = result : receiver.push(result);
      } catch (ignore) {
        restore();
        return receiver;
      } finally {
        drop();
      }
    }
  };

  const readKeyword = word => {
    for (let i = 0; i < word.length; i++) {
      if (source[offset + i] !== word[i]) {
        throw 'Unexpected token "' + word + '"';
      }
    }
    offset += word.length;
    readSpace();
    return word;
  };

  const readChar = (char) => {
    if (source[offset] !== char) throw 'Unexpected char "' + char + '"';
    offset++;
    readSpace();
    return char;
  };

  const readNoop = () => {};

  const readCommentMultiple = () => {
    let i = 0;
    if (source[offset + i++] !== '/' || source[offset + i++] !== '*') return false;
    do {
      record(source[offset + i]);
      while (offset + i < source.length && source[offset + i++] !== '*') {
        record(source[offset + i]);
      }
    } while (offset + i < source.length && source[offset + i] !== '/');
    offset += i + 1;
    return true;
  };

  const readCommentSharp = () => {
    let i = 0;
    if (source[offset + i++] !== '#') return false;
    while (source[offset + i] !== '\n' && source[offset + i] !== '\r') offset++;
    offset += i;
    return true;
  };

  const readCommentDoubleSlash = () => {
    let i = 0;
    if (source[offset + i++] !== '/' || source[offset + i++] !== '/') return false;
    while (source[offset + i] !== '\n' && source[offset + i] !== '\r') offset++;
    offset += i;
    return true;
  };

  const readSpace = () => {
    for (;;) {
      let byte = source[offset];
      record(byte);
      if (byte === '\n' || byte === '\r' || byte === ' ' || byte === '\t') {
        offset++;
      } else {
        if (!readCommentMultiple() && !readCommentSharp() && !readCommentDoubleSlash()) return;
      }
    }
  };

  const readComma = () => {
    if (source[offset] === ',' || source[offset] === ';') {
      offset++;
      readSpace();
      return ',';
    }
  };

  const readTypedef = () => {
    let subject = readKeyword('typedef');
    let type = readType();
    let name = readName();
    readComma();
    return {subject, type, name};
  };

  const readType = () => readAnyOne(readTypeMap, readTypeList, readTypeNormal);

  const readTypeMap = () => {
    let name = readKeyword('map');
    readChar('<');
    let keyType = readType();
    readComma();
    let valueType = readType();
    readChar('>');
    return {name, keyType, valueType};
  };

  const readTypeList = () => {
    let name = readAnyOne(() => readKeyword('list'), () => readKeyword('set'));
    readChar('<');
    let valueType = readType();
    readChar('>');
    return {name, valueType};
  };

  const readTypeNormal = () => readName();

  const readName = () => {
    let i = 0;
    let byte = source[offset];
    while (
      (byte >= 'a' && byte <= 'z') ||
      byte === '.' ||
      byte === '_' ||
      (byte >= 'A' && byte <= 'Z') ||
      (byte >= '0' && byte <= '9')
    ) byte = source[offset + ++i];
    if (i === 0) throw 'Unexpected token on readName';
    let value = source.slice(offset, offset += i);
    readSpace();
    return value;
  };

  const readScope = () => {
    let i = 0;
    let byte = source[offset];
    while (
      (byte >= 'a' && byte <= 'z') ||
      byte === '_' ||
      (byte >= 'A' && byte <= 'Z') ||
      (byte >= '0' && byte <= '9') ||
      (byte === '*') ||
      (byte === '.')
    ) byte = source[offset + ++i];
    if (i === 0) throw 'Unexpected token on readScope';
    let value = source.slice(offset, offset += i);
    readSpace();
    return value;
  };

  const readNumberSign = () => {
    let result;
    if (source[offset] === '+' || source[offset] === '-') {
      result = source[offset];
      offset++;
    }
    return result;
  };

  const readIntegerValue = () => {
    let result = [];
    let sign = readNumberSign();
    if (sign !== void 0) result.push(sign);

    for (; ;) {
      let byte = source[offset];
      if ((byte >= '0' && byte <= '9')) {
        offset++;
        result.push(byte);
      } else if (
        byte === 'E' || byte === 'e' ||
        byte === 'X' || byte === 'x' ||
        byte === '.'
      ) {
        throw `Unexpected token ${byte} for integer value`;
      } else {
        if (result.length) {
          readSpace();
          return +result.join('');
        } else {
          throw 'Unexpected token ' + byte;
        }
      }
    }
  };

  const readDecimalValue = () => {
    let result = [];
    let sign = readNumberSign();
    if (sign !== void 0) result.push(sign);

    for (;;) {
      let byte = source[offset];
      if ((byte >= '0' && byte <= '9') || byte === '.') {
        offset++;
        result.push(byte);
      } else {
        if (result.length) {
          readSpace();
          return +result.join('');
        } else {
          throw 'Unexpected token ' + byte;
        }
      }
    }
  };

  const readEnotationValue = () => {
    let result = [];
    if (source[offset] === '-') {
      result.push(source[offset]);
      offset++;
    }

    for (;;) {
      let byte = source[offset];
      if ((byte >= '0' && byte <= '9') || byte === '.') {
        result.push(byte);
        offset++;
      } else {
        break;
      }
    }

    if (source[offset] !== 'e' && source[offset] !== 'E') throw 'Unexpected token';
    result.push(source[offset]);
    offset++;

    for (;;) {
      let byte = source[offset];
      if (byte >= '0' && byte <= '9') {
        offset++;
        result.push(byte);
      } else {
        if (result.length) {
          readSpace();
          return +result.join('');
        } else {
          throw 'Unexpected token ' + byte;
        }
      }
    }
  };

  const readHexadecimalValue = () => {
    let result = [];
    if (source[offset] === '-') {
      result.push(source[offset]);
      offset++;
    }

    if (source[offset] !== '0') throw 'Unexpected token';
    result.push(source[offset]);
    offset++;

    if (source[offset] !== 'x' && source[offset] !== 'X') throw 'Unexpected token';
    result.push(source[offset]);
    offset++;

    for (;;) {
      let byte = source[offset];
      if (
        (byte >= '0' && byte <= '9') ||
        (byte >= 'A' && byte <= 'F') ||
        (byte >= 'a' && byte <= 'f')
      ) {
        offset++;
        result.push(byte);
      } else {
        if (result.length) {
          readSpace();
          return +result.join('');
        } else {
          throw 'Unexpected token ' + byte;
        }
      }
    }
  };

  const readBooleanValue = () => JSON.parse(readAnyOne(() => readKeyword('true'), () => readKeyword('false')));

  const readRefValue = () => {
    let list = [readName()];
    readUntilThrow(() => {
      readChar('.');
      list.push(readName());
    });
    return {'=': list};
  };

  const readStringValue = () => {
    let receiver = [];
    let start;
    while (source[offset] != null) {
      let byte = source[offset++];
      if (receiver.length) {
        if (byte === start) {
          receiver.push(byte);
          readSpace();
          return receiver.slice(1, -1).join('');
        } else if (byte === '\\') {
          receiver.push(byte);
          offset++;
          receiver.push(source[offset++]);
        } else {
          receiver.push(byte);
        }
      } else {
        if (byte === '"' || byte === '\'') {
          start = byte;
          receiver.push(byte);
        } else {
          throw 'Unexpected token ILLEGAL';
        }
      }
    }
    throw 'Unterminated string value';
  };

  const readListValue = () => {
    readChar('[');
    let list = readUntilThrow(() => {
      let value = readValue();
      readComma();
      return value;
    });
    readChar(']');
    return list;
  };

  const readMapValue = () => {
    readChar('{');
    let list = readUntilThrow(() => {
      let key = readValue();
      readChar(':');
      let value = readValue();
      readComma();
      return {key, value};
    });
    readChar('}');
    return list;
  };

  const readValue = () => readAnyOne(
    readHexadecimalValue, // This coming before readNumberValue is important, unfortunately
    readEnotationValue,   // This also needs to come before readNumberValue
    readDecimalValue,
    readIntegerValue,
    readStringValue,
    readBooleanValue,
    readListValue,
    readMapValue,
    readRefValue
  );

  const readConst = () => {
    let subject = readKeyword('const');
    let type = readType();
    let name = readName();
    readChar('=');
    let value = readValue();
    readComma();
    return {subject, type, name, value};
  };

  const readEnum = () => {
    let subject = readKeyword('enum');
    let name = readName();
    let items = readEnumBlock();
    return {subject, name, items};
  };

  const readEnumBlock = () => {
    readChar('{');
    let receiver = readUntilThrow(readEnumItem);
    readChar('}');
    return receiver;
  };

  const readEnumItem = () => {
    let name = readName();
    let value = readEnumValue();
    readComma();
    let result = {name};
    if (value !== void 0) result.value = value;
    return result;
  };

  const readEnumValue = () => {
    let beginning = offset;
    try {
      readChar('=');
    } catch (ignore) {
      offset = beginning;
      return;
    }
    return readAnyOne(readHexadecimalValue, readIntegerValue);
  };

  const readAssign = () => {
    try {
      save();
      readChar('=');
      return readValue();
    } catch (ignore) {
      restore();
    } finally {
      drop();
    }
  };

  const readStruct = () => {
    let subject = readKeyword('struct');
    let name = readName();
    let items = readStructLikeBlock();
    return {subject, name, items};
  };

  const readStructLikeBlock = () => {
    readChar('{');
    let receiver = readUntilThrow(readStructLikeItem);
    readChar('}');
    return receiver;
  };

  const readStructLikeItem = () => {
    let id;
    try {
      id = readAnyOne(readHexadecimalValue, readIntegerValue);
      readChar(':');
    } catch (err) {

    }

    let option = readAnyOne(() => readKeyword('required'), () => readKeyword('optional'), readNoop);
    let type = readType();
    let name = readName();
    let defaultValue = readAssign();
    readComma();
    let result = {type, name};
    if (id !== void 0) result.id = id;
    if (option !== void 0) result.option = option;
    if (defaultValue !== void 0) result.defaultValue = defaultValue;
    return result;
  };

  const readUnion = () => {
    let subject = readKeyword('union');
    let name = readName();
    let items = readStructLikeBlock();
    return {subject, name, items};
  };

  const readException = () => {
    let subject = readKeyword('exception');
    let name = readName();
    let items = readStructLikeBlock();
    return {subject, name, items};
  };

  const readExtends = () => {
    try {
      save();
      readKeyword('extends');
      let name = readRefValue()['='].join('.');
      return name;
    } catch (ignore) {
      restore();
      return;
    } finally {
      drop();
    }
  };

  const readService = () => {
    let subject = readKeyword('service');
    let name = readName();
    let extend = readExtends(); // extends is a reserved keyword
    let functions = readServiceBlock();
    let result = {subject, name};
    if (extend !== void 0) result.extends = extend;
    if (functions !== void 0) result.functions = functions;
    return result;
  };

  const readNamespace = () => {
    let subject = readKeyword('namespace');
    let name = readScope();
    let serviceName = readRefValue()['='].join('.');
    return {subject, name, serviceName};
  };

  const readInclude = () => {
    let subject = readKeyword('include');
    readSpace();
    let includePath = readQuotation();
    let name = includePath.replace(/^.*?([^/\\]*?)(?:\.thrift)?$/, '$1');
    readSpace();
    return {subject, name, path: includePath};
  };

  const readQuotation = () => {
    let quoteMatch;
    if (source[offset] === '"' || source[offset] === '\'') {
      quoteMatch = source[offset];
      offset++;
    } else {
      throw 'include error';
    }
    let i = offset;
    // Read until it finds a matching quote or end-of-file
    while (source[i] !== quoteMatch && source[i] != null) {
      i++;
    }
    if (source[i] === quoteMatch) {
      let value = source.slice(offset, i);
      offset = i + 1;
      return value;
    } else {
      throw 'include error';
    }
  };

  const readServiceBlock = () => {
    readChar('{');
    let receiver = readUntilThrow(readServiceItem, 'name');
    readChar('}');
    return receiver;
  };

  const readOneway = () => readKeyword('oneway');

  const readServiceItem = () => {
    let oneway = !!readAnyOne(readOneway, readNoop);
    let type = readType();
    let name = readName();
    let args = readServiceArgs();
    let throws = readServiceThrow();
    readComma();
    return {type, name, args, throws, oneway};
  };

  const readServiceArgs = () => {
    readChar('(');
    let receiver = readUntilThrow(readStructLikeItem);
    readChar(')');
    readSpace();
    return receiver;
  };

  const readServiceThrow = () => {
    try {
      save();
      readKeyword('throws');
      return readServiceArgs();
    } catch (ignore) {
      restore();
      return [];
    } finally {
      drop();
    }
  };

  const readSubject = () => {
    return readAnyOne(readTypedef, readConst, readEnum, readStruct, readUnion, readException, readService, readNamespace, readInclude);
  };

  const readThrift = () => {
    readSpace();
    let storage = {};
    for (;;) {
      try {
        let block = readSubject();
        let {subject, name} = block;
        if (!storage[subject]) storage[subject] = {};
        delete block.subject;
        delete block.name;
        switch (subject) {
          case 'exception':
          case 'struct':
          case 'union':
            storage[subject][name] = block.items;
            break;
          default:
            storage[subject][name] = block;
        }
      } catch (message) {
        let context = source.slice(offset, offset + 50);
        let line = Math.max(nCount, rCount) + 1;
        console.log("message=" + message + " context=" + context + " line=" + line);
        throw new ThriftFileParsingError({ message, context, line });
      } finally {
        if (source.length === offset) break;
      }
    }
    return storage;
  };

  return readThrift();

};
