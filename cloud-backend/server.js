/**
 * FSP Cloud Backend
 * 
 * A simple cloud server that serves fixture data for the Football Score Pro system.
 * This simulates a cloud backend that can provide tournament/fixture data to be
 * loaded into the local backend for match control.
 * 
 * Endpoints:
 * - GET /api/tournaments - List all tournaments
 * - GET /api/tournaments/:id - Get tournament details with fixtures
 * - GET /api/fixtures - List all fixtures
 * - GET /api/fixtures/:id - Get fixture details with teams and lineups
 * - GET /api/teams - List all teams
 * - GET /api/teams/:id - Get team with players
 */

import express from 'express';
import cors from 'cors';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3001;

// Error handling
process.on('uncaughtException', (err) => {
  // Log and exit: after an uncaught exception the process state is unknown
  console.error('Uncaught Exception:', err);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

app.use(cors());
app.use(express.json());

// Serve static assets (logos, kits)
app.use('/assets', express.static(path.join(__dirname, 'assets')));

// ============ Sample Data ============

const teams = {
  'mufc': {
    id: 'mufc',
    name: 'Manchester United',
    short_name: 'MUN',
    logo_url: '/logos/manchester-united.png',
    primary_color: '#DA291C',
    secondary_color: '#FBE122',
    players: [
      { id: 'mufc-1', name: 'André Onana', number: 24, position: 'GK', is_captain: false },
      { id: 'mufc-2', name: 'Diogo Dalot', number: 20, position: 'RB', is_captain: false },
      { id: 'mufc-3', name: 'Raphaël Varane', number: 19, position: 'CB', is_captain: false },
      { id: 'mufc-4', name: 'Lisandro Martínez', number: 6, position: 'CB', is_captain: false },
      { id: 'mufc-5', name: 'Luke Shaw', number: 23, position: 'LB', is_captain: false },
      { id: 'mufc-6', name: 'Casemiro', number: 18, position: 'CDM', is_captain: false },
      { id: 'mufc-7', name: 'Kobbie Mainoo', number: 37, position: 'CM', is_captain: false },
      { id: 'mufc-8', name: 'Bruno Fernandes', number: 8, position: 'CAM', is_captain: true },
      { id: 'mufc-9', name: 'Antony', number: 21, position: 'RW', is_captain: false },
      { id: 'mufc-10', name: 'Marcus Rashford', number: 10, position: 'LW', is_captain: false },
      { id: 'mufc-11', name: 'Rasmus Højlund', number: 11, position: 'ST', is_captain: false },
      { id: 'mufc-12', name: 'Tom Heaton', number: 22, position: 'GK', is_captain: false },
      { id: 'mufc-13', name: 'Victor Lindelöf', number: 2, position: 'CB', is_captain: false },
      { id: 'mufc-14', name: 'Harry Maguire', number: 5, position: 'CB', is_captain: false },
      { id: 'mufc-15', name: 'Aaron Wan-Bissaka', number: 29, position: 'RB', is_captain: false },
      { id: 'mufc-16', name: 'Scott McTominay', number: 39, position: 'CM', is_captain: false },
      { id: 'mufc-17', name: 'Mason Mount', number: 7, position: 'CAM', is_captain: false },
      { id: 'mufc-18', name: 'Alejandro Garnacho', number: 17, position: 'LW', is_captain: false },
    ]
  },
  'lfc': {
    id: 'lfc',
    name: 'Liverpool FC',
    short_name: 'LIV',
    logo_url: '/logos/liverpool.png',
    primary_color: '#C8102E',
    secondary_color: '#00B2A9',
    players: [
      { id: 'lfc-1', name: 'Alisson Becker', number: 1, position: 'GK', is_captain: false },
      { id: 'lfc-2', name: 'Trent Alexander-Arnold', number: 66, position: 'RB', is_captain: false },
      { id: 'lfc-3', name: 'Virgil van Dijk', number: 4, position: 'CB', is_captain: true },
      { id: 'lfc-4', name: 'Ibrahima Konaté', number: 5, position: 'CB', is_captain: false },
      { id: 'lfc-5', name: 'Andy Robertson', number: 26, position: 'LB', is_captain: false },
      { id: 'lfc-6', name: 'Wataru Endō', number: 3, position: 'CDM', is_captain: false },
      { id: 'lfc-7', name: 'Alexis Mac Allister', number: 10, position: 'CM', is_captain: false },
      { id: 'lfc-8', name: 'Dominik Szoboszlai', number: 8, position: 'CAM', is_captain: false },
      { id: 'lfc-9', name: 'Mohamed Salah', number: 11, position: 'RW', is_captain: false },
      { id: 'lfc-10', name: 'Luis Díaz', number: 7, position: 'LW', is_captain: false },
      { id: 'lfc-11', name: 'Darwin Núñez', number: 9, position: 'ST', is_captain: false },
      { id: 'lfc-12', name: 'Caoimhín Kelleher', number: 62, position: 'GK', is_captain: false },
      { id: 'lfc-13', name: 'Joe Gomez', number: 2, position: 'CB', is_captain: false },
      { id: 'lfc-14', name: 'Jarell Quansah', number: 78, position: 'CB', is_captain: false },
      { id: 'lfc-15', name: 'Kostas Tsimikas', number: 21, position: 'LB', is_captain: false },
      { id: 'lfc-16', name: 'Curtis Jones', number: 17, position: 'CM', is_captain: false },
      { id: 'lfc-17', name: 'Harvey Elliott', number: 19, position: 'RW', is_captain: false },
      { id: 'lfc-18', name: 'Cody Gakpo', number: 18, position: 'LW', is_captain: false },
    ]
  },
  'mci': {
    id: 'mci',
    name: 'Manchester City',
    short_name: 'MCI',
    logo_url: '/logos/manchester-city.png',
    primary_color: '#6CABDD',
    secondary_color: '#1C2C5B',
    players: [
      { id: 'mci-1', name: 'Ederson', number: 31, position: 'GK', is_captain: false },
      { id: 'mci-2', name: 'Kyle Walker', number: 2, position: 'RB', is_captain: false },
      { id: 'mci-3', name: 'Rúben Dias', number: 3, position: 'CB', is_captain: false },
      { id: 'mci-4', name: 'John Stones', number: 5, position: 'CB', is_captain: false },
      { id: 'mci-5', name: 'Joško Gvardiol', number: 24, position: 'LB', is_captain: false },
      { id: 'mci-6', name: 'Rodri', number: 16, position: 'CDM', is_captain: false },
      { id: 'mci-7', name: 'Kevin De Bruyne', number: 17, position: 'CM', is_captain: true },
      { id: 'mci-8', name: 'Bernardo Silva', number: 20, position: 'CAM', is_captain: false },
      { id: 'mci-9', name: 'Phil Foden', number: 47, position: 'RW', is_captain: false },
      { id: 'mci-10', name: 'Jack Grealish', number: 10, position: 'LW', is_captain: false },
      { id: 'mci-11', name: 'Erling Haaland', number: 9, position: 'ST', is_captain: false },
      { id: 'mci-12', name: 'Stefan Ortega', number: 18, position: 'GK', is_captain: false },
      { id: 'mci-13', name: 'Manuel Akanji', number: 25, position: 'CB', is_captain: false },
      { id: 'mci-14', name: 'Nathan Aké', number: 6, position: 'CB', is_captain: false },
      { id: 'mci-15', name: 'Rico Lewis', number: 82, position: 'RB', is_captain: false },
      { id: 'mci-16', name: 'Mateo Kovačić', number: 8, position: 'CM', is_captain: false },
      { id: 'mci-17', name: 'Julián Álvarez', number: 19, position: 'ST', is_captain: false },
      { id: 'mci-18', name: 'Jeremy Doku', number: 11, position: 'LW', is_captain: false },
    ]
  },
  'ars': {
    id: 'ars',
    name: 'Arsenal FC',
    short_name: 'ARS',
    logo_url: '/logos/arsenal.png',
    primary_color: '#EF0107',
    secondary_color: '#063672',
    players: [
      { id: 'ars-1', name: 'David Raya', number: 22, position: 'GK', is_captain: false },
      { id: 'ars-2', name: 'Ben White', number: 4, position: 'RB', is_captain: false },
      { id: 'ars-3', name: 'William Saliba', number: 2, position: 'CB', is_captain: false },
      { id: 'ars-4', name: 'Gabriel Magalhães', number: 6, position: 'CB', is_captain: false },
      { id: 'ars-5', name: 'Oleksandr Zinchenko', number: 35, position: 'LB', is_captain: false },
      { id: 'ars-6', name: 'Declan Rice', number: 41, position: 'CDM', is_captain: false },
      { id: 'ars-7', name: 'Martin Ødegaard', number: 8, position: 'CAM', is_captain: true },
      { id: 'ars-8', name: 'Kai Havertz', number: 29, position: 'CM', is_captain: false },
      { id: 'ars-9', name: 'Bukayo Saka', number: 7, position: 'RW', is_captain: false },
      { id: 'ars-10', name: 'Gabriel Martinelli', number: 11, position: 'LW', is_captain: false },
      { id: 'ars-11', name: 'Gabriel Jesus', number: 9, position: 'ST', is_captain: false },
      { id: 'ars-12', name: 'Aaron Ramsdale', number: 1, position: 'GK', is_captain: false },
      { id: 'ars-13', name: 'Takehiro Tomiyasu', number: 18, position: 'RB', is_captain: false },
      { id: 'ars-14', name: 'Jurriën Timber', number: 12, position: 'CB', is_captain: false },
      { id: 'ars-15', name: 'Kieran Tierney', number: 3, position: 'LB', is_captain: false },
      { id: 'ars-16', name: 'Thomas Partey', number: 5, position: 'CDM', is_captain: false },
      { id: 'ars-17', name: 'Jorginho', number: 20, position: 'CM', is_captain: false },
      { id: 'ars-18', name: 'Leandro Trossard', number: 19, position: 'LW', is_captain: false },
    ]
  },
  'che': {
    id: 'che',
    name: 'Chelsea FC',
    short_name: 'CHE',
    logo_url: '/logos/chelsea.png',
    primary_color: '#034694',
    secondary_color: '#DBA111',
    players: [
      { id: 'che-1', name: 'Robert Sánchez', number: 1, position: 'GK', is_captain: false },
      { id: 'che-2', name: 'Reece James', number: 24, position: 'RB', is_captain: true },
      { id: 'che-3', name: 'Thiago Silva', number: 6, position: 'CB', is_captain: false },
      { id: 'che-4', name: 'Levi Colwill', number: 26, position: 'CB', is_captain: false },
      { id: 'che-5', name: 'Ben Chilwell', number: 21, position: 'LB', is_captain: false },
      { id: 'che-6', name: 'Moisés Caicedo', number: 25, position: 'CDM', is_captain: false },
      { id: 'che-7', name: 'Enzo Fernández', number: 8, position: 'CM', is_captain: false },
      { id: 'che-8', name: 'Cole Palmer', number: 20, position: 'CAM', is_captain: false },
      { id: 'che-9', name: 'Raheem Sterling', number: 17, position: 'RW', is_captain: false },
      { id: 'che-10', name: 'Mykhailo Mudryk', number: 10, position: 'LW', is_captain: false },
      { id: 'che-11', name: 'Nicolas Jackson', number: 15, position: 'ST', is_captain: false },
      { id: 'che-12', name: 'Đorđe Petrović', number: 28, position: 'GK', is_captain: false },
      { id: 'che-13', name: 'Malo Gusto', number: 27, position: 'RB', is_captain: false },
      { id: 'che-14', name: 'Axel Disasi', number: 2, position: 'CB', is_captain: false },
      { id: 'che-15', name: 'Marc Cucurella', number: 3, position: 'LB', is_captain: false },
      { id: 'che-16', name: 'Conor Gallagher', number: 23, position: 'CM', is_captain: false },
      { id: 'che-17', name: 'Noni Madueke', number: 11, position: 'RW', is_captain: false },
      { id: 'che-18', name: 'Christopher Nkunku', number: 18, position: 'ST', is_captain: false },
    ]
  },
  'tot': {
    id: 'tot',
    name: 'Tottenham Hotspur',
    short_name: 'TOT',
    logo_url: '/logos/tottenham.png',
    primary_color: '#132257',
    secondary_color: '#FFFFFF',
    players: [
      { id: 'tot-1', name: 'Guglielmo Vicario', number: 13, position: 'GK', is_captain: false },
      { id: 'tot-2', name: 'Pedro Porro', number: 23, position: 'RB', is_captain: false },
      { id: 'tot-3', name: 'Cristian Romero', number: 17, position: 'CB', is_captain: false },
      { id: 'tot-4', name: 'Micky van de Ven', number: 37, position: 'CB', is_captain: false },
      { id: 'tot-5', name: 'Destiny Udogie', number: 38, position: 'LB', is_captain: false },
      { id: 'tot-6', name: 'Yves Bissouma', number: 8, position: 'CDM', is_captain: false },
      { id: 'tot-7', name: 'Pape Matar Sarr', number: 29, position: 'CM', is_captain: false },
      { id: 'tot-8', name: 'James Maddison', number: 10, position: 'CAM', is_captain: false },
      { id: 'tot-9', name: 'Dejan Kulusevski', number: 21, position: 'RW', is_captain: false },
      { id: 'tot-10', name: 'Son Heung-min', number: 7, position: 'LW', is_captain: true },
      { id: 'tot-11', name: 'Richarlison', number: 9, position: 'ST', is_captain: false },
      { id: 'tot-12', name: 'Fraser Forster', number: 20, position: 'GK', is_captain: false },
      { id: 'tot-13', name: 'Emerson Royal', number: 12, position: 'RB', is_captain: false },
      { id: 'tot-14', name: 'Eric Dier', number: 15, position: 'CB', is_captain: false },
      { id: 'tot-15', name: 'Ben Davies', number: 33, position: 'LB', is_captain: false },
      { id: 'tot-16', name: 'Oliver Skipp', number: 4, position: 'CDM', is_captain: false },
      { id: 'tot-17', name: 'Brennan Johnson', number: 19, position: 'RW', is_captain: false },
      { id: 'tot-18', name: 'Timo Werner', number: 16, position: 'LW', is_captain: false },
    ]
  },
  // Nepali Teams with full kit data
  'dhangadhi': {
    id: 'dhangadhi',
    name: 'Dhangadhi F.C.',
    short_name: 'DFC',
    logo_url: '/assets/logos/dhangadhi.png',
    primary_color: '#1e3a8a',
    secondary_color: '#fbbf24',
    kits: [
      {
        type: 'home',
        image_url: '/assets/kits/dhangadhi_home.png',
        primary_color: '#1e3a8a',
        secondary_color: '#fbbf24',
        brand_color: '#1e3a8a'
      },
      {
        type: 'away',
        image_url: '/assets/kits/dhangadhi_away.png',
        primary_color: '#fbbf24',
        secondary_color: '#1e3a8a',
        brand_color: '#fbbf24'
      },
      {
        type: 'third',
        image_url: '/assets/kits/dhangadhi_third.png',
        primary_color: '#ffffff',
        secondary_color: '#1e3a8a',
        brand_color: '#1e3a8a'
      }
    ],
    players: [
      { id: 'dfc-1', name: 'Ram Bahadur Thapa', number: 1, position: 'GK', is_captain: false },
      { id: 'dfc-2', name: 'Sunil Shrestha', number: 2, position: 'RB', is_captain: false },
      { id: 'dfc-3', name: 'Bikram Lama', number: 3, position: 'CB', is_captain: false },
      { id: 'dfc-4', name: 'Anil Gurung', number: 4, position: 'CB', is_captain: true },
      { id: 'dfc-5', name: 'Prakash Rai', number: 5, position: 'LB', is_captain: false },
      { id: 'dfc-6', name: 'Deepak Tamang', number: 6, position: 'CDM', is_captain: false },
      { id: 'dfc-7', name: 'Suman Magar', number: 7, position: 'CM', is_captain: false },
      { id: 'dfc-8', name: 'Rajan Karki', number: 8, position: 'CAM', is_captain: false },
      { id: 'dfc-9', name: 'Nabin Thapa', number: 9, position: 'RW', is_captain: false },
      { id: 'dfc-10', name: 'Kiran Limbu', number: 10, position: 'LW', is_captain: false },
      { id: 'dfc-11', name: 'Roshan Bhandari', number: 11, position: 'ST', is_captain: false },
      { id: 'dfc-12', name: 'Binod Rana', number: 12, position: 'GK', is_captain: false },
      { id: 'dfc-13', name: 'Hari Sharma', number: 13, position: 'CB', is_captain: false },
      { id: 'dfc-14', name: 'Manoj Dahal', number: 14, position: 'CM', is_captain: false },
      { id: 'dfc-15', name: 'Sabin KC', number: 15, position: 'RW', is_captain: false },
      { id: 'dfc-16', name: 'Ashok Poudel', number: 16, position: 'ST', is_captain: false },
      { id: 'dfc-17', name: 'Bibek Chaudhary', number: 17, position: 'LB', is_captain: false },
      { id: 'dfc-18', name: 'Dinesh Basnet', number: 18, position: 'CDM', is_captain: false },
    ]
  },
  'ktm-rayzrs': {
    id: 'ktm-rayzrs',
    name: 'Kathmandu Rayzrs FC',
    short_name: 'KRZ',
    logo_url: '/assets/logos/ktm_rayzrs.png',
    primary_color: '#1e40af',
    secondary_color: '#dc2626',
    kits: [
      {
        type: 'home',
        image_url: '/assets/kits/ktm_rayzrs_home.png',
        primary_color: '#a21caf',
        secondary_color: '#dc2626',
        brand_color: '#1e40af'
      },
      {
        type: 'away',
        image_url: '/assets/kits/ktm_rayzrs_away.png',
        primary_color: '#f97316',
        secondary_color: '#1e3a5f',
        brand_color: '#f97316'
      },
      {
        type: 'third',
        image_url: '/assets/kits/ktm_rayzrs_third.png',
        primary_color: '#d4a574',
        secondary_color: '#1e3a5f',
        brand_color: '#0ea5e9'
      }
    ],
    players: [
      { id: 'krz-1', name: 'Kiran Chemjong', number: 1, position: 'GK', is_captain: false },
      { id: 'krz-2', name: 'Ananta Tamang', number: 2, position: 'RB', is_captain: false },
      { id: 'krz-3', name: 'Suman Aryal', number: 3, position: 'CB', is_captain: true },
      { id: 'krz-4', name: 'Tej Tamang', number: 4, position: 'CB', is_captain: false },
      { id: 'krz-5', name: 'Ranjit Dhimal', number: 5, position: 'LB', is_captain: false },
      { id: 'krz-6', name: 'Bimal Gharti Magar', number: 6, position: 'CDM', is_captain: false },
      { id: 'krz-7', name: 'Anjan Bista', number: 7, position: 'CM', is_captain: false },
      { id: 'krz-8', name: 'Nawayug Shrestha', number: 8, position: 'CAM', is_captain: false },
      { id: 'krz-9', name: 'Aashish Lama', number: 9, position: 'RW', is_captain: false },
      { id: 'krz-10', name: 'Bharat Khawas', number: 10, position: 'LW', is_captain: false },
      { id: 'krz-11', name: 'Abhishek Rijal', number: 11, position: 'ST', is_captain: false },
      { id: 'krz-12', name: 'Bikash Khawas', number: 12, position: 'GK', is_captain: false },
      { id: 'krz-13', name: 'Rohit Chand', number: 13, position: 'CB', is_captain: false },
      { id: 'krz-14', name: 'Santosh Tamang', number: 14, position: 'CM', is_captain: false },
      { id: 'krz-15', name: 'Bishal Rai', number: 15, position: 'RW', is_captain: false },
      { id: 'krz-16', name: 'Manish Dangi', number: 16, position: 'ST', is_captain: false },
      { id: 'krz-17', name: 'Sudip Gurung', number: 17, position: 'LB', is_captain: false },
      { id: 'krz-18', name: 'Pujan Uperkoti', number: 18, position: 'CDM', is_captain: false },
    ]
  }
};

const tournaments = {
  'pl-2024': {
    id: 'pl-2024',
    name: 'Premier League 2024/25',
    short_name: 'PL',
    season: '2024/25',
    year: '2024',
    country: 'England',
    logo_url: '/assets/logos/premier-league.png',
    start_date: '2024-08-17',
    end_date: '2025-05-25',
    sponsor: 'EA Sports',
    hashtag: '#PremierLeague',
    tagline: 'The Best League in the World',
    teams: ['mufc', 'lfc', 'mci', 'ars', 'che', 'tot'],
    fixtures: ['fix-001', 'fix-002', 'fix-003', 'fix-004', 'fix-005', 'fix-006'],
    available_officials: [
      { name: 'Michael Oliver', role: 'referee' },
      { name: 'Anthony Taylor', role: 'referee' },
      { name: 'Craig Pawson', role: 'referee' },
      { name: 'Stuart Burt', role: 'assistant_referee' },
      { name: 'Gary Beswick', role: 'assistant_referee' },
      { name: 'Paul Tierney', role: 'var_referee' }
    ],
    available_commentators: [
      { name: 'Martin Tyler', role: 'commentator' },
      { name: 'Peter Drury', role: 'commentator' },
      { name: 'Gary Neville', role: 'co-commentator' },
      { name: 'Jamie Carragher', role: 'co-commentator' }
    ],
    available_hosts: [
      { name: 'Gary Lineker', role: 'presenter' },
      { name: 'Kelly Cates', role: 'presenter' },
      { name: 'Laura Woods', role: 'presenter' }
    ]
  },
  'facup-2024': {
    id: 'facup-2024',
    name: 'FA Cup 2024/25',
    short_name: 'FAC',
    season: '2024/25',
    year: '2024',
    country: 'England',
    logo_url: '/assets/logos/fa-cup.png',
    start_date: '2024-11-01',
    end_date: '2025-05-17',
    sponsor: 'Emirates',
    hashtag: '#EmiratesFACup',
    tagline: 'The Magic of the Cup',
    teams: ['mufc', 'lfc', 'mci', 'ars', 'che', 'tot'],
    fixtures: ['fix-007', 'fix-008'],
    available_officials: [
      { name: 'Stuart Attwell', role: 'referee' },
      { name: 'Jarred Gillett', role: 'referee' }
    ],
    available_commentators: [
      { name: 'Guy Mowbray', role: 'commentator' },
      { name: 'Steve Wilson', role: 'commentator' },
      { name: 'Alan Shearer', role: 'co-commentator' }
    ],
    available_hosts: [
      { name: 'Mark Chapman', role: 'presenter' },
      { name: 'Gabby Logan', role: 'presenter' }
    ]
  },
  'npl-2024': {
    id: 'npl-2024',
    name: 'Nepal Premier League 2024',
    short_name: 'NPL',
    season: '2024',
    year: '2024',
    country: 'Nepal',
    logo_url: '/assets/logos/npl.png',
    start_date: '2024-11-01',
    end_date: '2024-12-15',
    sponsor: 'Ncell',
    hashtag: '#NPL2024',
    tagline: 'Football for Nepal',
    teams: ['dhangadhi', 'ktm-rayzrs'],
    fixtures: ['fix-009'],
    available_officials: [
      { name: 'Bikash Thapa', role: 'referee' },
      { name: 'Deepak Karki', role: 'assistant_referee' },
      { name: 'Sanjay Shrestha', role: 'assistant_referee' },
      { name: 'Ramesh Bhandari', role: 'fourth_official' }
    ],
    available_commentators: [
      { name: 'Rajan Shrestha', role: 'commentator' },
      { name: 'Bimal Gharti Magar', role: 'co-commentator' },
      { name: 'Sunil Chhetri', role: 'guest_commentator' },
      { name: 'Anil Gurung', role: 'commentator' }
    ],
    available_hosts: [
      { name: 'Samrat Karki', role: 'presenter' },
      { name: 'Prashant Tamrakar', role: 'presenter' }
    ]
  }
};

const fixtures = {
  'fix-001': {
    id: 'fix-001',
    tournament_id: 'pl-2024',
    home_team_id: 'mufc',
    away_team_id: 'lfc',
    venue: 'Old Trafford',
    scheduled_date: '2024-12-15T15:00:00Z',
    matchday: 16,
    status: 'scheduled',
    officials: {
      referee: 'Michael Oliver',
      assistant_referee_1: 'Stuart Burt',
      assistant_referee_2: 'Simon Bennett',
      fourth_official: 'Andy Madley',
      var_referee: 'Paul Tierney',
      avar_referee: 'Lee Betts'
    },
    commentators: {
      commentators_1st: ['Martin Tyler', 'Gary Neville'],
      commentators_2nd: ['Peter Drury', 'Jamie Carragher']
    },
    hosts: ['Kelly Cates', 'Gary Lineker'],
    guests: [
      { name: 'Rio Ferdinand', title: 'Former Player' },
      { name: 'Roy Keane', title: 'Former Captain' }
    ],
    organizers: ['Premier League', 'Sky Sports']
  },
  'fix-002': {
    id: 'fix-002',
    tournament_id: 'pl-2024',
    home_team_id: 'mci',
    away_team_id: 'ars',
    venue: 'Etihad Stadium',
    scheduled_date: '2024-12-15T17:30:00Z',
    matchday: 16,
    status: 'scheduled',
    officials: {
      referee: 'Anthony Taylor',
      assistant_referee_1: 'Gary Beswick',
      assistant_referee_2: 'Adam Nunn',
      fourth_official: 'Robert Jones'
    },
    commentators: {
      commentators_1st: ['Peter Drury', 'Thierry Henry'],
      commentators_2nd: ['Jon Champion', 'Arsène Wenger']
    },
    hosts: ['Jake Humphrey'],
    organizers: ['Premier League', 'BT Sport']
  },
  'fix-003': {
    id: 'fix-003',
    tournament_id: 'pl-2024',
    home_team_id: 'che',
    away_team_id: 'tot',
    venue: 'Stamford Bridge',
    scheduled_date: '2024-12-14T12:30:00Z',
    matchday: 16,
    status: 'scheduled',
    officials: {
      referee: 'Craig Pawson',
      assistant_referee_1: 'Nick Hopton',
      assistant_referee_2: 'Derek Eaton',
      fourth_official: 'Thomas Bramall'
    },
    commentators: {
      commentators_1st: ['Clive Tyldesley', 'Andy Townsend']
    },
    hosts: ['Laura Woods'],
    organizers: ['Premier League']
  },
  'fix-004': {
    id: 'fix-004',
    tournament_id: 'pl-2024',
    home_team_id: 'lfc',
    away_team_id: 'mci',
    venue: 'Anfield',
    scheduled_date: '2024-12-22T16:30:00Z',
    matchday: 17,
    status: 'scheduled',
    officials: {
      referee: 'Michael Oliver',
      assistant_referee_1: 'Stuart Burt',
      assistant_referee_2: 'Dan Robathan',
      fourth_official: 'John Brooks'
    },
    commentators: {
      commentators_1st: ['Martin Tyler', 'Jamie Carragher'],
      commentators_2nd: ['Peter Drury', 'Micah Richards']
    },
    hosts: ['Gary Lineker', 'Gabby Logan'],
    guests: [
      { name: 'Steven Gerrard', title: 'Club Legend' },
      { name: 'Vincent Kompany', title: 'Former Captain' }
    ],
    organizers: ['Premier League', 'Sky Sports', 'BT Sport']
  },
  'fix-005': {
    id: 'fix-005',
    tournament_id: 'pl-2024',
    home_team_id: 'ars',
    away_team_id: 'mufc',
    venue: 'Emirates Stadium',
    scheduled_date: '2024-12-22T14:00:00Z',
    matchday: 17,
    status: 'scheduled',
    officials: {
      referee: 'David Coote',
      assistant_referee_1: 'Adrian Holmes',
      assistant_referee_2: 'Richard West',
      fourth_official: 'Tony Harrington'
    },
    commentators: {
      commentators_1st: ['Jon Champion', 'Martin Keown']
    },
    hosts: ['Des Kelly'],
    organizers: ['Premier League']
  },
  'fix-006': {
    id: 'fix-006',
    tournament_id: 'pl-2024',
    home_team_id: 'tot',
    away_team_id: 'che',
    venue: 'Tottenham Hotspur Stadium',
    scheduled_date: '2024-12-22T14:00:00Z',
    matchday: 17,
    status: 'scheduled',
    officials: {
      referee: 'Simon Hooper',
      assistant_referee_1: 'Mark Scholes',
      assistant_referee_2: 'Tim Wood',
      fourth_official: 'Sam Barrott'
    },
    commentators: {
      commentators_1st: ['Alistair Bruce-Ball', 'Jermaine Jenas']
    },
    hosts: ['Lynsey Hipgrave'],
    organizers: ['Premier League', 'TNT Sports']
  },
  'fix-007': {
    id: 'fix-007',
    tournament_id: 'facup-2024',
    home_team_id: 'mufc',
    away_team_id: 'mci',
    venue: 'Old Trafford',
    scheduled_date: '2025-01-11T15:00:00Z',
    round: 'Third Round',
    status: 'scheduled',
    officials: {
      referee: 'Stuart Attwell',
      assistant_referee_1: 'Harry Sherrington',
      assistant_referee_2: 'Matthew Wilkes',
      fourth_official: 'Graham Scott'
    },
    commentators: {
      commentators_1st: ['Guy Mowbray', 'Alan Shearer']
    },
    hosts: ['Mark Chapman'],
    guests: [
      { name: 'Wayne Rooney', title: 'Club Legend' }
    ],
    organizers: ['The FA', 'BBC Sport']
  },
  'fix-008': {
    id: 'fix-008',
    tournament_id: 'facup-2024',
    home_team_id: 'lfc',
    away_team_id: 'ars',
    venue: 'Anfield',
    scheduled_date: '2025-01-12T14:00:00Z',
    round: 'Third Round',
    status: 'scheduled',
    officials: {
      referee: 'Jarred Gillett',
      assistant_referee_1: 'Marc Perry',
      assistant_referee_2: 'Matthew Jones',
      fourth_official: 'Peter Bankes'
    },
    commentators: {
      commentators_1st: ['Steve Wilson', 'Danny Murphy']
    },
    hosts: ['Gabby Logan'],
    organizers: ['The FA', 'ITV Sport']
  },
  'fix-009': {
    id: 'fix-009',
    tournament_id: 'npl-2024',
    home_team_id: 'dhangadhi',
    away_team_id: 'ktm-rayzrs',
    venue: 'Dashrath Stadium',
    scheduled_date: '2024-12-10T14:00:00Z',
    matchday: 1,
    status: 'scheduled',
    officials: {
      referee: 'Bikash Thapa',
      assistant_referee_1: 'Deepak Karki',
      assistant_referee_2: 'Sanjay Shrestha',
      fourth_official: 'Ramesh Bhandari'
    },
    commentators: {
      commentators_1st: ['Rajan Shrestha', 'Bimal Gharti Magar'],
      commentators_2nd: ['Sunil Chhetri', 'Anil Gurung']
    },
    hosts: ['Samrat Karki', 'Prashant Tamrakar'],
    guests: [
      { name: 'Rohit Chand', title: 'National Team Captain' },
      { name: 'Hari Khadka', title: 'Football Legend' }
    ],
    organizers: ['ANFA', 'NPL Management', 'Kantipur Sports']
  }
};

// ============ API Routes ============

// Health check
app.get('/', (req, res) => {
  res.json({
    service: 'FSP Cloud Backend',
    version: '1.0.0',
    status: 'running',
    endpoints: {
      tournaments: '/api/tournaments',
      fixtures: '/api/fixtures',
      teams: '/api/teams'
    }
  });
});

// List all tournaments
app.get('/api/tournaments', (req, res) => {
  const tournamentList = Object.values(tournaments).map(t => ({
    id: t.id,
    name: t.name,
    season: t.season,
    country: t.country,
    logo_url: t.logo_url,
    fixture_count: t.fixtures.length,
    team_count: t.teams.length
  }));
  res.json(tournamentList);
});

// Get tournament with fixtures
app.get('/api/tournaments/:id', (req, res) => {
  const tournament = tournaments[req.params.id];
  if (!tournament) {
    return res.status(404).json({ error: 'Tournament not found' });
  }

  const tournamentFixtures = tournament.fixtures.map(fid => {
    const fix = fixtures[fid];
    return {
      ...fix,
      home_team: { id: fix.home_team_id, name: teams[fix.home_team_id]?.name, short_name: teams[fix.home_team_id]?.short_name },
      away_team: { id: fix.away_team_id, name: teams[fix.away_team_id]?.name, short_name: teams[fix.away_team_id]?.short_name }
    };
  });

  const tournamentTeams = tournament.teams.map(tid => ({
    id: tid,
    name: teams[tid]?.name,
    short_name: teams[tid]?.short_name,
    logo_url: teams[tid]?.logo_url
  }));

  res.json({
    ...tournament,
    fixtures: tournamentFixtures,
    teams: tournamentTeams
  });
});

// List all fixtures
app.get('/api/fixtures', (req, res) => {
  const { tournament_id, status } = req.query;
  
  let fixtureList = Object.values(fixtures).map(fix => ({
    ...fix,
    home_team: { id: fix.home_team_id, name: teams[fix.home_team_id]?.name, short_name: teams[fix.home_team_id]?.short_name },
    away_team: { id: fix.away_team_id, name: teams[fix.away_team_id]?.name, short_name: teams[fix.away_team_id]?.short_name },
    tournament_name: tournaments[fix.tournament_id]?.name
  }));

  if (tournament_id) {
    fixtureList = fixtureList.filter(f => f.tournament_id === tournament_id);
  }
  if (status) {
    fixtureList = fixtureList.filter(f => f.status === status);
  }

  res.json(fixtureList);
});

// Get fixture with full team and lineup data (ready for match creation)
app.get('/api/fixtures/:id', (req, res) => {
  const fixture = fixtures[req.params.id];
  if (!fixture) {
    return res.status(404).json({ error: 'Fixture not found' });
  }

  const homeTeam = teams[fixture.home_team_id];
  const awayTeam = teams[fixture.away_team_id];
  const tournament = tournaments[fixture.tournament_id];
  if (!homeTeam || !awayTeam || !tournament) {
    return res.status(500).json({ error: 'Fixture references a missing team or tournament' });
  }

  // Return full fixture data ready for match creation
  res.json({
    id: fixture.id,
    tournament: {
      id: tournament.id,
      name: tournament.name,
      short_name: tournament.short_name,
      season: tournament.season,
      year: tournament.year,
      sponsor: tournament.sponsor,
      hashtag: tournament.hashtag,
      tagline: tournament.tagline,
      logo_url: tournament.logo_url
    },
    venue: fixture.venue,
    scheduled_date: fixture.scheduled_date,
    matchday: fixture.matchday,
    round: fixture.round,
    status: fixture.status,
    // Officials
    officials: fixture.officials || {},
    // Commentators  
    commentators: fixture.commentators || {},
    // Hosts
    hosts: fixture.hosts || [],
    // Guests
    guests: fixture.guests || [],
    // Organizers
    organizers: fixture.organizers || [],
    // Available pools from tournament for selection dialogs
    available_officials: tournament.available_officials || [],
    available_commentators: tournament.available_commentators || [],
    available_hosts: tournament.available_hosts || [],
    home_team: {
      id: homeTeam.id,
      name: homeTeam.name,
      short_name: homeTeam.short_name,
      logo_url: homeTeam.logo_url,
      primary_color: homeTeam.primary_color,
      secondary_color: homeTeam.secondary_color,
      kits: homeTeam.kits || []
    },
    away_team: {
      id: awayTeam.id,
      name: awayTeam.name,
      short_name: awayTeam.short_name,
      logo_url: awayTeam.logo_url,
      primary_color: awayTeam.primary_color,
      secondary_color: awayTeam.secondary_color,
      kits: awayTeam.kits || []
    },
    home_lineup: homeTeam.players.slice(0, 11).map(p => ({
      ...p,
      is_starting: true
    })),
    away_lineup: awayTeam.players.slice(0, 11).map(p => ({
      ...p,
      is_starting: true
    })),
    home_substitutes: homeTeam.players.slice(11).map(p => ({
      ...p,
      is_starting: false
    })),
    away_substitutes: awayTeam.players.slice(11).map(p => ({
      ...p,
      is_starting: false
    }))
  });
});

// List all teams
app.get('/api/teams', (req, res) => {
  const teamList = Object.values(teams).map(t => ({
    id: t.id,
    name: t.name,
    short_name: t.short_name,
    logo_url: t.logo_url,
    primary_color: t.primary_color,
    player_count: t.players.length
  }));
  res.json(teamList);
});

// Get team with full roster
app.get('/api/teams/:id', (req, res) => {
  const team = teams[req.params.id];
  if (!team) {
    return res.status(404).json({ error: 'Team not found' });
  }
  res.json(team);
});

// ============ Start Server ============

app.listen(PORT, () => {
  console.log(`
╔════════════════════════════════════════════════════════════╗
║           FSP Cloud Backend - Running                       ║
╠════════════════════════════════════════════════════════════╣
║  URL: http://localhost:${PORT}                               ║
║                                                            ║
║  Endpoints:                                                ║
║    GET /api/tournaments      - List tournaments            ║
║    GET /api/tournaments/:id  - Tournament with fixtures    ║
║    GET /api/fixtures         - List all fixtures           ║
║    GET /api/fixtures/:id     - Fixture ready for match     ║
║    GET /api/teams            - List all teams              ║
║    GET /api/teams/:id        - Team with full roster       ║
╚════════════════════════════════════════════════════════════╝
  `);
});
