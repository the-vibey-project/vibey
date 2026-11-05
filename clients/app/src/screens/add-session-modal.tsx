// Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
/**
 * Bottom-sheet modal for adding attachments, configuring session permissions, selecting projects,
 * and toggling features (Research, Connectors, Skills, Memory, Health) matching the frontier AI mobile interface.
 */
import { useState } from 'react';
import {
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import type { VibeyProject } from '@vibey/core';
import { useTheme } from '../ui/theme';

export interface AddSessionModalProps {
  readonly visible: boolean;
  readonly onClose: () => void;
  readonly projects: readonly VibeyProject[];
  readonly selectedProjectId: string | null;
  readonly onSelectProject: (projectId: string | null) => void;
  readonly onAction?: (action: 'camera' | 'photos' | 'files') => void;
}

export function AddSessionModal(props: {
  readonly visible: boolean;
  readonly onClose: () => void;
  readonly projects: readonly VibeyProject[];
  readonly selectedProjectId: string | null;
  readonly onSelectProject: (projectId: string | null) => void;
  readonly onAction?: (action: 'camera' | 'photos' | 'files') => void;
}) {
  const { colors } = useTheme();
  const [research, setResearch] = useState(false);
  const [health, setHealth] = useState(true);
  const [projectPickerOpen, setProjectPickerOpen] = useState(false);

  const selectedProject = props.projects.find((p) => p.project_id === props.selectedProjectId);
  const projectName = selectedProject?.name ?? 'None';

  return (
    <Modal
      animationType="slide"
      transparent={true}
      visible={props.visible}
      onRequestClose={props.onClose}
    >
      <View style={styles.backdrop}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Dismiss sheet"
          style={styles.scrim}
          onPress={props.onClose}
        />
        <View
          style={[
            styles.sheet,
            { backgroundColor: colors.bg.surface, borderColor: colors.border.subtle },
          ]}
        >
          {/* Drag Handle */}
          <View style={styles.handleContainer}>
            <View style={[styles.handle, { backgroundColor: colors.border.strong }]} />
          </View>

          {/* Modal Header */}
          <View style={styles.header}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Close"
              onPress={props.onClose}
              style={styles.closeButton}
            >
              <Text style={[styles.closeIcon, { color: colors.text.primary }]}>✕</Text>
            </Pressable>
            <Text style={[styles.headerTitle, { color: colors.text.primary }]}>Add to session</Text>
            <View style={styles.headerSpacer} />
          </View>

          <ScrollView contentContainerStyle={styles.scrollContent}>
            {/* Quick Upload Tile Grid: Camera, Photos, Files */}
            <View style={styles.tilesRow}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Camera"
                style={[
                  styles.tile,
                  { backgroundColor: colors.bg.canvas, borderColor: colors.border.subtle },
                ]}
                onPress={() => {
                  props.onAction?.('camera');
                  props.onClose();
                }}
              >
                <Text style={styles.tileIcon}>📷</Text>
                <Text style={[styles.tileLabel, { color: colors.text.primary }]}>Camera</Text>
              </Pressable>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Photos"
                style={[
                  styles.tile,
                  { backgroundColor: colors.bg.canvas, borderColor: colors.border.subtle },
                ]}
                onPress={() => {
                  props.onAction?.('photos');
                  props.onClose();
                }}
              >
                <Text style={styles.tileIcon}>🖼️</Text>
                <Text style={[styles.tileLabel, { color: colors.text.primary }]}>Photos</Text>
              </Pressable>

              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Files"
                style={[
                  styles.tile,
                  { backgroundColor: colors.bg.canvas, borderColor: colors.border.subtle },
                ]}
                onPress={() => {
                  props.onAction?.('files');
                  props.onClose();
                }}
              >
                <Text style={styles.tileIcon}>📄</Text>
                <Text style={[styles.tileLabel, { color: colors.text.primary }]}>Files</Text>
              </Pressable>
            </View>

            {/* Group 1: Project, Permission, Devices */}
            <View
              style={[
                styles.group,
                { backgroundColor: colors.bg.canvas, borderColor: colors.border.subtle },
              ]}
            >
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Add to project"
                style={styles.row}
                onPress={() => setProjectPickerOpen((open) => !open)}
              >
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>📁</Text>
                  <View>
                    <Text style={[styles.rowTitle, { color: colors.text.primary }]}>
                      Add to project
                    </Text>
                    <Text style={[styles.rowSubtitle, { color: colors.text.secondary }]}>
                      {projectName}
                    </Text>
                  </View>
                </View>
                <Text style={[styles.rowChevron, { color: colors.text.tertiary }]}>›</Text>
              </Pressable>

              {projectPickerOpen ? (
                <View style={styles.pickerContainer}>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel="Select None project"
                    style={[
                      styles.pickerOption,
                      props.selectedProjectId === null && {
                        backgroundColor: colors.bg.surface,
                      },
                    ]}
                    onPress={() => {
                      props.onSelectProject(null);
                      setProjectPickerOpen(false);
                    }}
                  >
                    <Text
                      style={[
                        styles.pickerText,
                        {
                          color:
                            props.selectedProjectId === null
                              ? colors.accent.default
                              : colors.text.primary,
                        },
                      ]}
                    >
                      None (All projects)
                    </Text>
                  </Pressable>
                  {props.projects.map((proj) => (
                    <Pressable
                      key={proj.project_id}
                      accessibilityRole="button"
                      accessibilityLabel={`Select project ${proj.name}`}
                      style={[
                        styles.pickerOption,
                        props.selectedProjectId === proj.project_id && {
                          backgroundColor: colors.bg.surface,
                        },
                      ]}
                      onPress={() => {
                        props.onSelectProject(proj.project_id);
                        setProjectPickerOpen(false);
                      }}
                    >
                      <Text
                        style={[
                          styles.pickerText,
                          {
                            color:
                              props.selectedProjectId === proj.project_id
                                ? colors.accent.default
                                : colors.text.primary,
                          },
                        ]}
                      >
                        {proj.name} ({proj.phase})
                      </Text>
                    </Pressable>
                  ))}
                </View>
              ) : null}

              <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>✋</Text>
                  <View>
                    <Text style={[styles.rowTitle, { color: colors.text.primary }]}>
                      Permission
                    </Text>
                    <Text style={[styles.rowSubtitle, { color: colors.text.secondary }]}>
                      Manual
                    </Text>
                  </View>
                </View>
                <Text style={[styles.rowChevron, { color: colors.text.tertiary }]}>›</Text>
              </View>

              <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>💻</Text>
                  <View>
                    <Text style={[styles.rowTitle, { color: colors.text.primary }]}>Devices</Text>
                    <Text style={[styles.rowSubtitle, { color: colors.text.secondary }]}>
                      krypton desktop (macOS)
                    </Text>
                  </View>
                </View>
              </View>
            </View>

            {/* Group 2: Research, Connectors, Skills, Memory, Health */}
            <View
              style={[
                styles.group,
                { backgroundColor: colors.bg.canvas, borderColor: colors.border.subtle },
              ]}
            >
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>🔍</Text>
                  <Text style={[styles.rowTitle, { color: colors.text.primary }]}>Research</Text>
                </View>
                <Switch
                  accessibilityLabel="Research switch"
                  value={research}
                  onValueChange={setResearch}
                  trackColor={{ true: colors.accent.default, false: colors.border.subtle }}
                />
              </View>

              <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>🔌</Text>
                  <Text style={[styles.rowTitle, { color: colors.text.primary }]}>Connectors</Text>
                </View>
                <Text style={[styles.rowChevron, { color: colors.text.tertiary }]}>›</Text>
              </View>

              <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>⚡</Text>
                  <Text style={[styles.rowTitle, { color: colors.text.primary }]}>Skills</Text>
                </View>
                <Text style={[styles.rowChevron, { color: colors.text.tertiary }]}>›</Text>
              </View>

              <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>🧠</Text>
                  <View>
                    <Text style={[styles.rowTitle, { color: colors.text.primary }]}>Memory</Text>
                    <Text style={[styles.rowSubtitle, { color: colors.text.tertiary }]}>
                      Can't be changed for this session
                    </Text>
                  </View>
                </View>
                <Switch
                  accessibilityLabel="Memory disabled"
                  value={true}
                  disabled={true}
                  trackColor={{ true: colors.border.strong, false: colors.border.subtle }}
                />
              </View>

              <View style={[styles.divider, { backgroundColor: colors.border.subtle }]} />

              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>🤍</Text>
                  <Text style={[styles.rowTitle, { color: colors.text.primary }]}>Health</Text>
                </View>
                <Switch
                  accessibilityLabel="Health switch"
                  value={health}
                  onValueChange={setHealth}
                  trackColor={{ true: colors.accent.default, false: colors.border.subtle }}
                />
              </View>
            </View>
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: 'rgba(0,0,0,0.6)',
  },
  scrim: {
    ...StyleSheet.absoluteFill,
  },
  sheet: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    borderWidth: 1,
    borderBottomWidth: 0,
    maxHeight: '90%',
    paddingBottom: Platform.OS === 'ios' ? 32 : 16,
  },
  handleContainer: {
    alignItems: 'center',
    paddingVertical: 10,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingBottom: 12,
  },
  closeButton: {
    padding: 6,
    width: 36,
    alignItems: 'flex-start',
  },
  closeIcon: {
    fontSize: 18,
    fontWeight: '600',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '600',
    textAlign: 'center',
  },
  headerSpacer: {
    width: 36,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingBottom: 24,
    gap: 16,
  },
  tilesRow: {
    flexDirection: 'row',
    gap: 10,
    justifyContent: 'space-between',
  },
  tile: {
    flex: 1,
    height: 90,
    borderRadius: 16,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  tileIcon: {
    fontSize: 26,
  },
  tileLabel: {
    fontSize: 13,
    fontWeight: '500',
  },
  group: {
    borderRadius: 16,
    borderWidth: 1,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  rowLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    flex: 1,
  },
  rowIcon: {
    fontSize: 18,
  },
  rowTitle: {
    fontSize: 15,
    fontWeight: '500',
  },
  rowSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  rowChevron: {
    fontSize: 20,
    fontWeight: '300',
  },
  divider: {
    height: 1,
    marginLeft: 46,
  },
  pickerContainer: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 4,
  },
  pickerOption: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 8,
  },
  pickerText: {
    fontSize: 14,
    fontWeight: '500',
  },
});
