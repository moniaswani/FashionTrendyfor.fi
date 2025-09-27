// testDynamo.cjs
const AWS = require('aws-sdk');

const dynamodb = new AWS.DynamoDB({ region: 'eu-west-2' });

dynamodb.listTables({}, (err, data) => {
  if (err) console.error(err);
  else console.log(data);
});
