const { gql } = require('graphql-tag');

const typeDefs = gql`
  type Channel {
    id: ID!
    name: String!
    description: String
    createdAt: String!
    messages: [Message!]!
  }

  type Message {
    id: ID!
    title: String!
    content: String!
    channelId: ID!
    createdAt: String!
    channel: Channel!
  }

  type Query {
    channels: [Channel!]!
    channel(id: ID!): Channel
    messages(channelId: ID!): [Message!]!
    message(id: ID!): Message
  }

  type Mutation {
    createChannel(input: CreateChannelInput!): Channel!
    createMessage(input: CreateMessageInput!): Message!
    deleteChannel(id: ID!): Boolean!
    deleteMessage(id: ID!): Boolean!
  }

  input CreateChannelInput {
    name: String!
    description: String
  }

  input CreateMessageInput {
    title: String!
    content: String!
    channelId: ID!
  }
`;

module.exports = { typeDefs };
