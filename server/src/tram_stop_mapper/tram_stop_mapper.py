import difflib
import random
import string
from collections import defaultdict
from functools import cached_property

import overpy
from src.model import CityConfiguration, GTFSPackage
from src.tram_stop_mapper.exceptions import (
    TramStopMappingBuildError,
    TramStopMappingUnknownNodeException,
)
from src.tram_stop_mapper.tram_stop_mapping_errors import TramStopMappingErrors


class TramStopMapper:
    def __init__(
        self,
        city_configuration: CityConfiguration,
        gtfs_package: GTFSPackage,
        osm_relations_and_stops: overpy.Result,
    ):
        self._city_configuration = city_configuration
        self._gtfs_package = gtfs_package
        self._osm_relations_and_stops = osm_relations_and_stops

        self._stop_mapping: dict[str, set[int]] = {
            str(stop_id): set() for stop_id in self._gtfs_package.stops.index
        }
        self._first_stop_mapping: dict[str, set[int]] = defaultdict(set)
        self._last_stop_mapping: dict[str, set[int]] = defaultdict(set)

        self._mapping_errors = TramStopMappingErrors()
        self._longest_osm_relation_by_trip_id: dict[str, overpy.Relation] = {}
        self._longest_match_size_by_osm_relation: defaultdict[overpy.Relation, int] = (
            defaultdict(int)
        )

        self._build_tram_stop_mapping()

        if self._mapping_errors:
            raise TramStopMappingBuildError(self._mapping_errors)

    @cached_property
    def _osm_node_by_id(self):
        return {item.id: item for item in self._osm_relations_and_stops.get_nodes()}

    @cached_property
    def _stops_by_osm_relation(self):
        return {
            relation: [
                self._osm_node_by_id[member.ref]
                for member in relation.members
                if isinstance(member, overpy.RelationNode)
                and member.ref in self._osm_node_by_id
            ]
            for relation in self._osm_relations_and_stops.get_relations()
        }

    @staticmethod
    def _to_universal_stop_name(stop_name: str):
        """
        Due to differences in stop names between GTFS and OSM, for example
        the 'Meksyk (nż)' stop in GTFS is equivalent to 'Meksyk 01' on OSM,
        comparing stop names directly between these two datasets is impossible.
        The proposed solution to this problem is to convert both of these names
        to their universal form, in this case 'meksyk'.
        """

        return (
            stop_name.lower()
            .rstrip(string.digits)
            .replace(".", "")
            .replace(" ", "")
            .replace("(nż)", "")
        )

    @cached_property
    def _universal_stop_names_by_osm_relation(self):
        return {
            relation: [
                self._to_universal_stop_name(item.tags.get("name")) for item in stops
            ]
            for relation, stops in self._stops_by_osm_relation.items()
        }

    def _is_longer_match(
        self,
        longest_match: difflib.Match,
        longest_relation: overpy.Relation,
        current_match: difflib.Match,
        current_result: overpy.Relation,
    ):
        """
        Let's imagine a line which has two variants: A -> B and A -> B -> C.
        This occurs for example on line 50, which may terminate at Kurdwanów P+R (B)
        or at Borek Fałęcki (C). Both of these variants are represented by their own
        OSM relation.

        Notice that the stops of A -> B relation are a subsequence of the stops of
        A -> B -> C relation. This means that in case the trip is of A -> B variant,
        the match size of stops for A -> B and A -> B -> C relations will be equal,
        so this comparison is insufficient.

        In order to reliably track which relations are fully used, the *longest*
        relation is the one which has the most stops in common with the trip and
        has the largest utilization. Relation utilization is measured as the ratio
        between the stop sequence length in common with the trip and the relation
        stop count. This ensures that if the trip is of variant A -> B, the A -> B
        relation will be selected instead of A -> B -> C, as it will have the
        greater utilization.
        """

        if current_match.size >= 2 and longest_match.size != current_match.size:
            return longest_match.size < current_match.size

        longest_relation_stop_count = len(self._stops_by_osm_relation[longest_relation])
        longest_relation_utilization = longest_match.size / longest_relation_stop_count

        current_relation_stop_count = len(self._stops_by_osm_relation[current_result])
        current_relation_utilization = current_match.size / current_relation_stop_count

        return longest_relation_utilization <= current_relation_utilization

    def _find_longest_matching_relation(
        self,
        line_relations: list[overpy.Relation],
        gtfs_trip_stop_names: list[str],
    ):
        longest_match, longest_relation = difflib.Match(0, 0, 0), line_relations[0]

        for relation in line_relations:
            sequence_matcher = difflib.SequenceMatcher(
                None,
                gtfs_trip_stop_names,
                self._universal_stop_names_by_osm_relation[relation],
            )

            match_result = sequence_matcher.find_longest_match(
                0,
                len(gtfs_trip_stop_names),
                0,
                len(self._stops_by_osm_relation[relation]),
            )

            if self._is_longer_match(
                longest_match, longest_relation, match_result, relation
            ):
                longest_match, longest_relation = match_result, relation

        return longest_match, longest_relation

    def _add_trip_to_mapping(
        self, gtfs_trip_id: str, line_relations: list[overpy.Relation]
    ):
        gtfs_trip_stop_ids = self._gtfs_package.stop_id_sequence_by_trip_id[
            gtfs_trip_id
        ]
        gtfs_trip_stop_data = self._gtfs_package.stops.loc[gtfs_trip_stop_ids]
        gtfs_trip_stop_names = list(
            map(self._to_universal_stop_name, gtfs_trip_stop_data["stop_name"])
        )

        longest_match, longest_relation = self._find_longest_matching_relation(
            line_relations, gtfs_trip_stop_names
        )

        matched_gtfs_trip_stops = gtfs_trip_stop_data.iloc[
            longest_match.a : longest_match.a + longest_match.size
        ].index

        matched_osm_relation_stops = self._stops_by_osm_relation[longest_relation][
            longest_match.b : longest_match.b + longest_match.size
        ]

        for i, (gtfs_stop_id, osm_node) in enumerate(
            zip(matched_gtfs_trip_stops, matched_osm_relation_stops)
        ):
            # First and last stops can be ambiguous, we skip them in 1-to-1 mapping
            if not (0 < i < longest_match.size - 1):
                continue

            self._stop_mapping[gtfs_stop_id].add(osm_node.id)

        if (
            gtfs_trip_stop_names[1:-1]
            == self._universal_stop_names_by_osm_relation[longest_relation][1:-1]
        ):
            self._first_stop_mapping[gtfs_trip_stop_ids[0]].add(
                self._stops_by_osm_relation[longest_relation][0].id
            )
            self._last_stop_mapping[gtfs_trip_stop_ids[-1]].add(
                self._stops_by_osm_relation[longest_relation][-1].id
            )

        return longest_match.size, longest_relation

    def _update_relations_for_route(
        self,
        route_number: str,
        gtfs_route_id: str,
    ):
        line_relations = [
            item
            for item in self._stops_by_osm_relation
            if item.tags.get("ref") == route_number
        ]

        if not line_relations:
            self._mapping_errors.missing_relations_for_lines.add(route_number)
            return

        gtfs_trips_for_route = self._gtfs_package.trips[
            self._gtfs_package.trips["route_id"] == gtfs_route_id
        ]

        for gtfs_trip_id in gtfs_trips_for_route.index:
            longest_match_size, longest_relation = self._add_trip_to_mapping(
                str(gtfs_trip_id),
                line_relations,
            )

            self._longest_match_size_by_osm_relation[longest_relation] = max(
                self._longest_match_size_by_osm_relation[longest_relation],
                longest_match_size,
            )

            self._longest_osm_relation_by_trip_id[gtfs_trip_id] = longest_relation

    def _build_tram_stop_mapping(self):
        for (
            gtfs_stop_id,
            node_id,
        ) in self._city_configuration.custom_stop_mapping.items():
            self._stop_mapping[gtfs_stop_id].add(node_id)

        for gtfs_route_id, gtfs_route_row in self._gtfs_package.routes.iterrows():
            route_number = str(gtfs_route_row["route_long_name"])
            if route_number in self._city_configuration.ignored_gtfs_lines:
                continue

            self._update_relations_for_route(route_number, gtfs_route_id)

        for gtfs_stop_id, osm_node_ids in self._stop_mapping.items():
            match len(osm_node_ids):
                case 0:
                    self._mapping_errors.stops_without_mapping.add(gtfs_stop_id)
                case 1:
                    pass
                case _:
                    self._mapping_errors.nodes_with_conflict[gtfs_stop_id] = [
                        (self._osm_node_by_id[node_id].tags.get("name"), node_id)
                        for node_id in osm_node_ids
                    ]

        self._mapping_errors.stops_without_mapping = (
            self._mapping_errors.stops_without_mapping.difference(
                self._first_stop_mapping.keys()
            ).difference(self._last_stop_mapping.keys())
        )

        self._mapping_errors.underutilized_relations = {
            relation: [
                item.tags.get("name") for item in self._stops_by_osm_relation[relation]
            ]
            for relation, stops in self._stops_by_osm_relation.items()
            if self._longest_match_size_by_osm_relation[relation] < len(stops)
        }

    @cached_property
    def gtfs_stop_id_to_osm_node_id_mapping(self):
        return {
            gtfs_stop_id: next(iter(osm_node_ids))
            for gtfs_stop_id, osm_node_ids in self._stop_mapping.items()
            if len(osm_node_ids) == 1
        }

    @cached_property
    def first_gtfs_stop_id_to_osm_node_ids(self):
        return {
            gtfs_stop_id: sorted(node_ids)
            for gtfs_stop_id, node_ids in self._first_stop_mapping.items()
        }

    @cached_property
    def last_gtfs_stop_id_to_osm_node_ids(self):
        return {
            gtfs_stop_id: sorted(node_ids)
            for gtfs_stop_id, node_ids in self._last_stop_mapping.items()
        }

    def _get_node_id_for_trip_stop(
        self, gtfs_stop_id: str, gtfs_stop_sequence: int, total_stops: int
    ):
        if gtfs_stop_id in self.gtfs_stop_id_to_osm_node_id_mapping:
            return self.gtfs_stop_id_to_osm_node_id_mapping[gtfs_stop_id]

        if (
            gtfs_stop_id in self.first_gtfs_stop_id_to_osm_node_ids
            and gtfs_stop_id in self.last_gtfs_stop_id_to_osm_node_ids
        ):
            return (
                random.choice(self.first_gtfs_stop_id_to_osm_node_ids[gtfs_stop_id])
                if gtfs_stop_sequence < total_stops / 2
                else random.choice(self.last_gtfs_stop_id_to_osm_node_ids[gtfs_stop_id])
            )

        if gtfs_stop_id in self.first_gtfs_stop_id_to_osm_node_ids:
            return random.choice(self.first_gtfs_stop_id_to_osm_node_ids[gtfs_stop_id])
        if gtfs_stop_id in self.last_gtfs_stop_id_to_osm_node_ids:
            return random.choice(self.last_gtfs_stop_id_to_osm_node_ids[gtfs_stop_id])

        return None

    def get_stop_nodes_by_gtfs_trip_id(self):
        stop_nodes_by_gtfs_trip_id: dict[str, list[int]] = {}
        gtfs_trips_with_missing_node_ids: dict[str, list[int | None]] = {}

        for (
            gtfs_trip_id,
            longest_relation,
        ) in self._longest_osm_relation_by_trip_id.items():
            relation_stop_nodes = self._stops_by_osm_relation[longest_relation]
            relation_stop_names = self._universal_stop_names_by_osm_relation[
                longest_relation
            ]

            gtfs_trip_stops = self._gtfs_package.stop_id_sequence_by_trip_id[
                gtfs_trip_id
            ]
            gtfs_trip_stop_data = self._gtfs_package.stops.loc[gtfs_trip_stops]
            gtfs_trip_stop_names = [
                self._to_universal_stop_name(item)
                for item in gtfs_trip_stop_data["stop_name"]
            ]

            if gtfs_trip_stop_names[1:-1] == relation_stop_names[1:-1]:
                stop_nodes_by_gtfs_trip_id[gtfs_trip_id] = [
                    item.id for item in relation_stop_nodes
                ]
                continue

            stop_nodes_from_mapping = [
                self._get_node_id_for_trip_stop(stop, i, len(gtfs_trip_stops))
                for i, stop in enumerate(gtfs_trip_stops)
            ]

            if None not in stop_nodes_from_mapping:
                stop_nodes_by_gtfs_trip_id[gtfs_trip_id] = stop_nodes_from_mapping
            else:
                gtfs_trips_with_missing_node_ids[gtfs_trip_id] = stop_nodes_from_mapping

        if gtfs_trips_with_missing_node_ids:
            raise TramStopMappingUnknownNodeException(gtfs_trips_with_missing_node_ids)

        return stop_nodes_by_gtfs_trip_id
