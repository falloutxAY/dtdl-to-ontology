using System.Text.Json;
using DTDLParser;
using DTDLParser.Models;

if (args.Length != 1)
{
    Console.Error.WriteLine("Usage: DtdlOracle <conformance-cases.json> | --geospatial");
    return 2;
}

if (args[0] == "--geospatial")
{
    var schemas = new Dictionary<string, object>();
    foreach (var name in new[] { "point", "lineString", "polygon", "multiPoint", "multiLineString", "multiPolygon" })
    {
        var text = "{\"@context\":\"dtmi:dtdl:context;3\",\"@id\":\"dtmi:oracle:Geo;1\",\"@type\":\"Interface\",\"contents\":[{\"@type\":\"Property\",\"name\":\"shape\",\"schema\":\"" + name + "\"}]}";
        var parsed = new ModelParser().Parse(new[] { text });
        var property = parsed.Values.OfType<DTPropertyInfo>().Single();
        schemas[name] = Describe(property.Schema);
    }
    Console.WriteLine(JsonSerializer.Serialize(schemas, new JsonSerializerOptions { WriteIndented = true }));
    return 0;
}

using var document = JsonDocument.Parse(File.ReadAllText(args[0]));
var results = new List<object>();
foreach (var entry in document.RootElement.GetProperty("cases").EnumerateArray())
{
    var name = entry.GetProperty("id").GetString();
    var model = entry.GetProperty("model").GetRawText();
    try
    {
        var parser = new ModelParser();
        parser.Parse(new[] { model });
        results.Add(new { id = name, accepted = true, errors = Array.Empty<string>() });
    }
    catch (ParsingException error)
    {
        results.Add(new
        {
            id = name,
            accepted = false,
            errors = error.Errors.Select(e => e.ValidationID.ToString()).Order().ToArray()
        });
    }
    catch (ResolutionException error)
    {
        results.Add(new { id = name, accepted = false, errors = new[] { error.Message } });
    }
}

Console.WriteLine(JsonSerializer.Serialize(new
{
    parser = "DTDLParser",
    version = "1.1.3",
    cases = results
}, new JsonSerializerOptions { WriteIndented = true }));
return 0;

static object Describe(DTSchemaInfo schema)
{
    var result = new Dictionary<string, object>
    {
        ["@id"] = schema.Id.ToString(),
        ["@type"] = schema.EntityKind.ToString()
    };
    switch (schema)
    {
        case DTObjectInfo obj:
            result["fields"] = obj.Fields.Select(field => new
            {
                name = field.Name,
                schema = Describe(field.Schema)
            }).ToArray();
            break;
        case DTArrayInfo array:
            result["elementSchema"] = Describe(array.ElementSchema);
            break;
        case DTEnumInfo enumeration:
            result["valueSchema"] = Describe(enumeration.ValueSchema);
            result["enumValues"] = enumeration.EnumValues.Select(value => new
            {
                name = value.Name,
                enumValue = value.EnumValue
            }).ToArray();
            break;
        default:
            var name = schema.EntityKind.ToString();
            return char.ToLowerInvariant(name[0]) + name[1..];
    }
    return result;
}
